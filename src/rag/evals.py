"""Reproducible Ragas ID-based context-recall benchmark."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from rag.ingestion.chunking import RecursiveChunker
from rag.ingestion.pipeline import IngestionPipeline
from rag.ingestion.providers import ExtractiveSummaryProvider, HashEmbeddingProvider
from rag.ingestion.utils import DocumentParser
from rag.ingestion.vector_store import QdrantVectorStore
from rag.retrieval.dense import DenseRetriever
from rag.retrieval.pipeline import HybridRetriever
from rag.retrieval.reranker import LexicalReranker
from rag.retrieval.sparse import BM25Retriever

LOGGER = logging.getLogger(__name__)
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    chunk_size: int
    chunk_count: int
    top_k: int
    context_recall: float
    per_question: list[float]


def _score_value(raw_score: Any) -> float:
    value = getattr(raw_score, "value", raw_score)
    return float(value)


def _normalize_evidence(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


async def evaluate_chunk_size(
    *,
    chunk_size: int,
    data_dir: Path,
    golden_path: Path,
    database_root: Path,
    top_k: int,
) -> EvaluationResult:
    try:
        from ragas import SingleTurnSample
        from ragas.metrics import IDBasedContextRecall
    except ImportError as exc:
        message = "Install evaluation dependencies with: pip install -e '.[eval]'"
        raise RuntimeError(message) from exc

    collection = f"aws_support_eval_{chunk_size}"
    store = QdrantVectorStore(
        collection_name=collection,
        path=database_root / f"qdrant-{chunk_size}",
    )
    embedder = HashEmbeddingProvider()
    pipeline = IngestionPipeline(
        parser=DocumentParser(),
        chunker=RecursiveChunker(
            chunk_size=chunk_size,
            chunk_overlap=max(32, chunk_size // 8),
        ),
        summarizer=ExtractiveSummaryProvider(),
        embedder=embedder,
        store=store,
    )
    await pipeline.run(data_dir)

    dense = DenseRetriever(embedder=embedder, store=store)
    sparse = BM25Retriever(store=store)
    await sparse.refresh()
    retriever = HybridRetriever(
        dense=dense,
        sparse=sparse,
        reranker=LexicalReranker(),
    )
    records = await store.list_records()
    golden_json = await asyncio.to_thread(golden_path.read_text, encoding="utf-8")
    golden_rows = json.loads(golden_json)
    metric = IDBasedContextRecall()
    scores: list[float] = []

    for row in golden_rows:
        raw_evidence = row["reference_evidence"]
        evidence_items = raw_evidence if isinstance(raw_evidence, list) else [raw_evidence]
        normalized_evidence = [_normalize_evidence(str(item)) for item in evidence_items]
        reference_ids = sorted(
            {
                str(record.metadata["chunk_hash"])
                for record in records
                if any(
                    evidence in _normalize_evidence(record.text) for evidence in normalized_evidence
                )
            }
        )
        retrieved = await retriever.retrieve(str(row["question"]), limit=top_k)
        retrieved_ids = [result.chunk_hash for result in retrieved]
        if not reference_ids:
            LOGGER.warning("No reference chunk found for question: %s", row["question"])
            scores.append(0.0)
            continue
        sample = SingleTurnSample(
            retrieved_context_ids=retrieved_ids,
            reference_context_ids=reference_ids,
        )
        score = _score_value(await metric.single_turn_ascore(sample))
        scores.append(score)
        LOGGER.info("chunk_size=%d recall=%.3f question=%s", chunk_size, score, row["question"])

    mean_score = sum(scores) / len(scores) if scores else 0.0
    LOGGER.info(
        "Ragas Context Recall | chunk_size=%d | chunks=%d | top_k=%d | score=%.3f",
        chunk_size,
        len(records),
        top_k,
        mean_score,
    )
    return EvaluationResult(
        chunk_size=chunk_size,
        chunk_count=len(records),
        top_k=top_k,
        context_recall=mean_score,
        per_question=scores,
    )


async def async_run(arguments: argparse.Namespace) -> int:
    results = []
    for chunk_size in arguments.chunk_sizes:
        results.append(
            await evaluate_chunk_size(
                chunk_size=chunk_size,
                data_dir=arguments.data_dir,
                golden_path=arguments.golden,
                database_root=arguments.database_root,
                top_k=arguments.top_k,
            )
        )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps([asdict(result) for result in results], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    LOGGER.info("Wrote evaluation report to %s", arguments.output)
    return 0


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate retrieval with Ragas Context Recall")
    parser.add_argument("--chunk-sizes", type=int, nargs="+", default=[256, 512])
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--data-dir", type=Path, default=REPOSITORY_ROOT / "data" / "sample")
    parser.add_argument(
        "--golden",
        type=Path,
        default=REPOSITORY_ROOT / "evals" / "golden_dataset.json",
    )
    parser.add_argument(
        "--database-root",
        type=Path,
        default=REPOSITORY_ROOT / ".rag_data" / "eval",
    )
    parser.add_argument("--output", type=Path, default=REPOSITORY_ROOT / "evals" / "results.json")
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
        LOGGER.exception("Evaluation failed")
        return 1
