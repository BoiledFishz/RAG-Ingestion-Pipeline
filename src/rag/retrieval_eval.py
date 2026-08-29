"""Fifteen-question benchmark for Dense, reranked Dense, and Hybrid retrieval."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from rag.ingestion.chunking import RecursiveChunker
from rag.ingestion.pipeline import IngestionPipeline
from rag.ingestion.providers import ExtractiveSummaryProvider, HashEmbeddingProvider
from rag.ingestion.utils import DocumentParser
from rag.ingestion.vector_store import QdrantVectorStore, VectorRecord
from rag.retrieval.contracts import RetrievalMode, SearchResult
from rag.retrieval.dense import DenseRetriever
from rag.retrieval.filters import FilterPolicy
from rag.retrieval.pipeline import RetrievalConfig, RetrievalPipeline
from rag.retrieval.reranker import LexicalReranker
from rag.retrieval.sparse import BM25Retriever

LOGGER = logging.getLogger(__name__)
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class GoldenRow:
    identifier: str
    category: str
    answerable: bool
    question: str
    expected_sources: tuple[str, ...]
    reference_evidence: tuple[str, ...]
    filters: dict[str, str | int | float | bool]


@dataclass(frozen=True, slots=True)
class Observation:
    row: GoldenRow
    results: list[SearchResult]
    latency_ms: float
    top_score: float | None


@dataclass(frozen=True, slots=True)
class ModeMetrics:
    mode: str
    candidate_k: int
    rerank_k: int
    evaluation_k: int
    production_final_k: int
    calibrated_threshold: float
    recall_at_5: float
    recall_at_10: float
    mrr: float
    context_precision: float
    average_latency_ms: float
    refusal_accuracy: float
    answer_acceptance_accuracy: float


def _load_golden(path: Path) -> list[GoldenRow]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or len(raw) < 15:
        raise ValueError("retrieval golden dataset must contain at least 15 rows")
    rows: list[GoldenRow] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("each golden row must be an object")
        raw_filters = item.get("filters", {})
        if not isinstance(raw_filters, dict):
            raise ValueError("golden row filters must be an object")
        filters: dict[str, str | int | float | bool] = {}
        for key, value in raw_filters.items():
            if isinstance(value, (str, int, float, bool)):
                filters[str(key)] = value
        rows.append(
            GoldenRow(
                identifier=str(item["id"]),
                category=str(item["category"]),
                answerable=bool(item["answerable"]),
                question=str(item["question"]),
                expected_sources=tuple(str(value) for value in item["expected_sources"]),
                reference_evidence=tuple(
                    str(value) for value in item.get("reference_evidence", [])
                ),
                filters=filters,
            )
        )
    return rows


def _score(result: SearchResult) -> float:
    return result.rerank_score if result.rerank_score is not None else result.score


def _calibrate_threshold(observations: list[Observation]) -> float:
    values = sorted(
        {observation.top_score for observation in observations if observation.top_score is not None}
    )
    if not values:
        return 1.0
    candidates = [values[0] - 1e-9, values[-1] + 1e-9]
    candidates.extend(
        (left + right) / 2
        for left, right in zip(values, values[1:], strict=False)
    )

    best_threshold = candidates[0]
    best_accuracy = -1.0
    for threshold in candidates:
        correct = 0
        for observation in observations:
            predicted_answerable = (
                observation.top_score is not None
                and observation.top_score >= threshold
            )
            correct += predicted_answerable == observation.row.answerable
        accuracy = correct / len(observations)
        if accuracy > best_accuracy or (
            accuracy == best_accuracy and threshold > best_threshold
        ):
            best_accuracy = accuracy
            best_threshold = threshold
    return best_threshold


def _normalize_evidence(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _evidence_matches_chunk(evidence: str, chunk_text: str) -> bool:
    normalized_evidence = _normalize_evidence(evidence)
    normalized_chunk = _normalize_evidence(chunk_text)
    if not normalized_evidence or not normalized_chunk:
        return False
    if normalized_evidence in normalized_chunk or normalized_chunk in normalized_evidence:
        return True
    evidence_tokens = set(re.findall(r"[a-z0-9_.:/-]+|[\u4e00-\u9fff]", normalized_evidence))
    chunk_tokens = set(re.findall(r"[a-z0-9_.:/-]+|[\u4e00-\u9fff]", normalized_chunk))
    shorter_count = min(len(evidence_tokens), len(chunk_tokens))
    return (
        shorter_count >= 5
        and len(evidence_tokens.intersection(chunk_tokens)) / shorter_count >= 0.8
    )


def _build_reference_chunk_index(
    rows: list[GoldenRow], records: list[VectorRecord]
) -> dict[str, frozenset[str]]:
    index: dict[str, frozenset[str]] = {}
    for row in rows:
        if not row.answerable:
            index[row.identifier] = frozenset()
            continue
        matches = {
            str(record.metadata.get("chunk_id") or record.metadata.get("chunk_hash", ""))
            for record in records
            if str(record.metadata.get("source_file", "")) in row.expected_sources
            and any(
                _evidence_matches_chunk(evidence, record.text)
                for evidence in row.reference_evidence
            )
        }
        matches.discard("")
        if not matches:
            raise ValueError(
                f"No evidence chunk could be resolved for golden row {row.identifier}"
            )
        index[row.identifier] = frozenset(matches)
    return index


def _contains_expected_chunk(
    row: GoldenRow,
    result: SearchResult,
    reference_chunk_ids: dict[str, frozenset[str]],
) -> bool:
    return result.chunk_id in reference_chunk_ids[row.identifier]


def _metrics(
    label: str,
    observations: list[Observation],
    config: RetrievalConfig,
    reference_chunk_ids: dict[str, frozenset[str]],
    production_final_k: int,
) -> ModeMetrics:
    threshold = _calibrate_threshold(observations)
    answerable = [item for item in observations if item.row.answerable]
    unanswerable = [item for item in observations if not item.row.answerable]

    recall_5 = 0.0
    recall_10 = 0.0
    reciprocal_ranks = 0.0
    precision = 0.0
    accepted_answerable = 0
    for observation in answerable:
        ranks = [
            rank
            for rank, result in enumerate(observation.results, start=1)
            if _contains_expected_chunk(observation.row, result, reference_chunk_ids)
        ]
        recall_5 += float(any(rank <= 5 for rank in ranks))
        recall_10 += float(any(rank <= 10 for rank in ranks))
        reciprocal_ranks += 1.0 / ranks[0] if ranks else 0.0
        top_five = observation.results[:5]
        precision += (
            sum(
                _contains_expected_chunk(observation.row, result, reference_chunk_ids)
                for result in top_five
            )
            / len(top_five)
            if top_five
            else 0.0
        )
        accepted_answerable += (
            observation.top_score is not None
            and observation.top_score >= threshold
        )

    refused_unanswerable = sum(
        observation.top_score is None or observation.top_score < threshold
        for observation in unanswerable
    )
    answerable_count = max(len(answerable), 1)
    unanswerable_count = max(len(unanswerable), 1)
    return ModeMetrics(
        mode=label,
        candidate_k=config.candidate_k,
        rerank_k=config.rerank_k,
        evaluation_k=config.final_k,
        production_final_k=production_final_k,
        calibrated_threshold=threshold,
        recall_at_5=recall_5 / answerable_count,
        recall_at_10=recall_10 / answerable_count,
        mrr=reciprocal_ranks / answerable_count,
        context_precision=precision / answerable_count,
        average_latency_ms=sum(item.latency_ms for item in observations)
        / max(len(observations), 1),
        refusal_accuracy=refused_unanswerable / unanswerable_count,
        answer_acceptance_accuracy=accepted_answerable / answerable_count,
    )


async def _evaluate_mode(
    *,
    label: str,
    mode: RetrievalMode,
    rows: list[GoldenRow],
    dense: DenseRetriever,
    sparse: BM25Retriever,
    config: RetrievalConfig,
    use_reranker: bool,
    reference_chunk_ids: dict[str, frozenset[str]],
    production_final_k: int,
) -> ModeMetrics:
    pipeline = RetrievalPipeline(
        dense=dense,
        sparse=sparse,
        reranker=LexicalReranker() if use_reranker else None,
        config=config,
        filter_policy=dense.filter_policy,
    )
    observations: list[Observation] = []
    for row in rows:
        started = time.perf_counter()
        outcome = await pipeline.retrieve(
            row.question,
            mode=mode,
            filters=row.filters,
        )
        latency_ms = (time.perf_counter() - started) * 1_000
        top_score = _score(outcome.results[0]) if outcome.results else None
        observations.append(
            Observation(
                row=row,
                results=outcome.results,
                latency_ms=latency_ms,
                top_score=top_score,
            )
        )
    metrics = _metrics(
        label,
        observations,
        config,
        reference_chunk_ids,
        production_final_k,
    )
    LOGGER.info(
        (
            "%s | Recall@5=%.3f Recall@10=%.3f MRR=%.3f "
            "ContextPrecision=%.3f Latency=%.2fms RefusalAccuracy=%.3f"
        ),
        label,
        metrics.recall_at_5,
        metrics.recall_at_10,
        metrics.mrr,
        metrics.context_precision,
        metrics.average_latency_ms,
        metrics.refusal_accuracy,
    )
    return metrics


async def async_run(arguments: argparse.Namespace) -> int:
    rows = _load_golden(arguments.golden)
    store = QdrantVectorStore(
        path=arguments.database,
        collection_name=arguments.collection,
    )
    embedder = HashEmbeddingProvider()
    parser = DocumentParser(
        tesseract_cmd=os.getenv("TESSERACT_CMD") or None,
        ocr_languages=os.getenv("OCR_LANGUAGES", "eng"),
    )
    ingestion = IngestionPipeline(
        parser=parser,
        chunker=RecursiveChunker(
            chunk_size=arguments.chunk_size,
            chunk_overlap=arguments.chunk_overlap,
        ),
        summarizer=ExtractiveSummaryProvider(),
        embedder=embedder,
        store=store,
    )
    try:
        await ingestion.run(arguments.data_dir)
        reference_chunk_ids = _build_reference_chunk_index(
            rows,
            await store.list_records(),
        )
        policy = FilterPolicy()
        config = RetrievalConfig(
            candidate_k=arguments.candidate_k,
            rerank_k=arguments.rerank_k,
            final_k=max(arguments.final_k, 10),
            rrf_rank_constant=arguments.rrf_rank_constant,
        )
        dense = DenseRetriever(
            embedder=embedder,
            store=store,
            candidate_k=config.candidate_k,
            final_k=config.final_k,
            filter_policy=policy,
        )
        sparse = BM25Retriever(
            store=store,
            candidate_k=config.candidate_k,
            final_k=config.final_k,
            filter_policy=policy,
        )
        await sparse.refresh()
        specifications: list[tuple[str, RetrievalMode, bool]] = [
            ("dense", "dense", False),
            ("dense+rerank", "dense", True),
            ("sparse+rerank", "sparse", True),
            ("hybrid+rerank", "hybrid", True),
        ]
        results = [
            await _evaluate_mode(
                label=label,
                mode=mode,
                rows=rows,
                dense=dense,
                sparse=sparse,
                config=config,
                use_reranker=use_reranker,
                reference_chunk_ids=reference_chunk_ids,
                production_final_k=arguments.final_k,
            )
            for label, mode, use_reranker in specifications
        ]
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(
            json.dumps([asdict(result) for result in results], indent=2) + "\n",
            encoding="utf-8",
        )
        LOGGER.info("Wrote retrieval evaluation to %s", arguments.output)
        return 0
    finally:
        await store.close()


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate production retrieval modes")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=REPOSITORY_ROOT / "data" / "aws_support_test_corpus" / "data",
    )
    parser.add_argument(
        "--golden",
        type=Path,
        default=REPOSITORY_ROOT / "evals" / "retrieval_golden_dataset.json",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=REPOSITORY_ROOT / ".rag_data" / "retrieval-eval-v2",
    )
    parser.add_argument("--collection", default="aws_support_retrieval_eval")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "evals" / "retrieval_results.json",
    )
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--chunk-overlap", type=int, default=64)
    parser.add_argument("--candidate-k", type=int, default=30)
    parser.add_argument("--rerank-k", type=int, default=20)
    parser.add_argument("--final-k", type=int, default=5)
    parser.add_argument("--rrf-rank-constant", type=int, default=60)
    parser.add_argument("--log-level", default="INFO")
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    arguments = build_argument_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(arguments.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    try:
        return asyncio.run(async_run(arguments))
    except Exception:
        LOGGER.exception("Retrieval evaluation failed")
        return 1
