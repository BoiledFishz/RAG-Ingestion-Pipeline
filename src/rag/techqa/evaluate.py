"""Full-corpus retrieval comparison on official questions, without answer leakage."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import time
from collections.abc import Awaitable
from pathlib import Path
from typing import Any

import httpx

from rag.retrieval.contracts import SearchResult
from rag.retrieval.fusion import reciprocal_rank_fusion
from rag.techqa.data import ROOT, question_text, questions
from rag.techqa.retrieval import (
    FullDenseRetriever,
    FullSparseRetriever,
    TechQAReranker,
    open_index,
)

LOGGER = logging.getLogger(__name__)


def metrics(results: list[SearchResult], expected: str | None) -> dict[str, float | None]:
    ids = [str(r.metadata.get("techqa_document_id")) for r in results]
    return {
        "hit_at_5": float(expected in ids[:5]) if expected else None,
        "hit_at_10": float(expected in ids[:10]) if expected else None,
        "mrr": (1 / (ids.index(expected) + 1) if expected in ids else 0) if expected else None,
        "context_precision_at_5": (sum(v == expected for v in ids[:5]) / 5) if expected else None,
    }


async def evaluate(
    split: str, limit: int, semantic: bool, output: Path, resume: bool = False,
) -> dict[str, Any]:
    rows = questions(split)
    if limit:
        rows = rows[:limit]
    index = open_index()
    dense, sparse = FullDenseRetriever(), FullSparseRetriever(index)
    async with httpx.AsyncClient(timeout=120) as client:
        ready = await client.get(dense.url + "/healthz")
        ready.raise_for_status()
        semantic_manifest = ready.json()
    if (not semantic_manifest.get("complete")
            or semantic_manifest.get("scope") != "full"
            or semantic_manifest["documents"] != int(index.manifest["document_count"])):
        raise ValueError("Full semantic benchmark requires complete, matching full-corpus indexes")
    reranker = TechQAReranker(semantic)
    observations = []
    await asyncio.to_thread(output.mkdir, parents=True, exist_ok=True)
    protocol = {
        "split": split, "limit": limit, "semantic_reranker": semantic,
        "embedding_id": semantic_manifest["embedding_id"],
        "questions_sha256": hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(),
        "candidate_k": 30, "rerank_k": 20, "rrf_constant": 60,
    }
    configuration = output / "run_config.json"
    previous: dict[str, dict[str, Any]] = {}
    attempt_path = output / "attempts.jsonl"
    if resume:
        if json.loads(configuration.read_text(encoding="utf-8")) != protocol:
            raise ValueError("Checkpoint model, questions or retrieval protocol changed")
        if not attempt_path.exists() and (output / "runs.jsonl").exists():
            attempt_path.write_bytes((output / "runs.jsonl").read_bytes())
        if attempt_path.exists():
            for line in attempt_path.read_text(encoding="utf-8").splitlines():
                saved_attempt = json.loads(line)
                previous[saved_attempt["id"]] = saved_attempt
    else:
        configuration.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
    initial_failures = sum(bool(item["error"]) for item in previous.values())
    reused = 0
    # Save progress after each question. An interrupted run is never labelled complete.
    with attempt_path.open("a" if resume else "w", encoding="utf-8") as handle:
        for row in rows:
            saved = previous.get(row["QUESTION_ID"])
            if saved is not None and not saved["error"] and len(saved["modes"]) == 4:
                observations.append(saved)
                reused += 1
                continue
            started = time.perf_counter()
            query = question_text(row)
            item: dict[str, Any] = {
                "id": row["QUESTION_ID"],
                "answerable": row["ANSWERABLE"] == "Y",
                "expected_document": str(row["DOCUMENT"]) if row["ANSWERABLE"] == "Y" else None,
                "modes": {},
                "error": None,
            }
            expected = str(row["DOCUMENT"]) if item["answerable"] else None
            try:

                async def timed(
                    operation: Awaitable[list[SearchResult]],
                ) -> tuple[list[SearchResult], float]:
                    start = time.perf_counter()
                    result = await operation
                    return result, (time.perf_counter() - start) * 1000

                (d, dt), (s, st) = await asyncio.gather(
                    timed(dense.retrieve(query, limit=30)), timed(sparse.retrieve(query, limit=30))
                )
                fused = reciprocal_rank_fusion([d, s], rank_constant=60, limit=30)
                dr, drt = await timed(reranker.rerank(query, d, limit=20))
                hr, hrt = await timed(reranker.rerank(query, fused, limit=20))
                for name, results, latency in [
                    ("dense", d[:10], dt),
                    ("bm25", s[:10], st),
                    ("dense_rerank", dr[:10], dt + drt),
                    ("hybrid_rerank", hr[:10], max(dt, st) + hrt),
                ]:
                    item["modes"][name] = {
                        **metrics(results, expected),
                        "latency_ms": latency,
                        "top_score": results[0].score if results else None,
                        "document_ids": [r.metadata.get("techqa_document_id") for r in results],
                        "chunk_ids": [r.chunk_id for r in results],
                        "candidate_scores": [r.score for r in results],
                    }
            except Exception as exc:
                LOGGER.exception("TechQA %s failed", row["QUESTION_ID"])
                item["error"] = str(exc)
            item["latency_ms"] = (time.perf_counter() - started) * 1000
            observations.append(item)
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
            handle.flush()
            LOGGER.info(
                "%s completed (%d/%d) error=%s",
                row["QUESTION_ID"],
                len(observations),
                len(rows),
                item["error"],
            )
    answerable = [r for r in observations if r["answerable"]]
    summary: dict[str, Any] = {
        "dataset": "IBM TechQA",
        "split": split,
        "scope": index.manifest,
        "semantic_index": semantic_manifest,
        "questions": len(rows),
        "answerable": len(answerable),
        "semantic_reranker": semantic,
        "dense_embedding": semantic_manifest["encoder"],
        "protocol": "open retrieval over entire corpus; official DOC_IDS not supplied; "
        "N labels refer to official candidate pools, not proof of absence in full corpus",
        "error_count": sum(bool(r["error"]) for r in observations),
        "complete": len(observations) == len(rows),
        "resumed": resume, "reused_questions": reused,
        "prior_failed_questions": initial_failures,
        "modes": {},
        "runtime": {"candidate_k": 30, "rerank_k": 20, "reported_k": 10,
                    "device": "CUDA encoding; exact Faiss CPU search",
                    "reranker": "nomic" if semantic else "lexical"},
    }
    for mode in ["dense", "bm25", "dense_rerank", "hybrid_rerank"]:
        summary["modes"][mode] = {
            key: sum(float(r["modes"].get(mode, {}).get(key) or 0) for r in answerable)
            / max(len(answerable), 1)
            for key in ["hit_at_5", "hit_at_10", "mrr", "context_precision_at_5"]
        }
        summary["modes"][mode]["average_latency_ms"] = sum(
            float(r["modes"].get(mode, {}).get("latency_ms", r["latency_ms"])) for r in observations
        ) / max(len(observations), 1)
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (output / "runs.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in observations),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["train", "dev", "validation"], default="dev")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--lexical", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "evals/techqa_semantic_full")
    args = parser.parse_args()
    result = asyncio.run(evaluate(
        args.split, args.limit, not args.lexical, args.output, args.resume,
    ))
    LOGGER.info("TechQA summary: %s", result)
    return int(bool(result["error_count"]))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    raise SystemExit(main())
