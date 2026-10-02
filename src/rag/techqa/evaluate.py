"""Full-corpus retrieval comparison on official questions, without answer leakage."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from collections.abc import Awaitable
from pathlib import Path
from typing import Any

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


async def evaluate(split: str, limit: int, semantic: bool, output: Path) -> dict[str, Any]:
    rows = questions(split)
    if limit:
        rows = rows[:limit]
    index = open_index()
    dense, sparse = FullDenseRetriever(), FullSparseRetriever(index)
    reranker = TechQAReranker(semantic)
    observations = []
    await asyncio.to_thread(output.mkdir, parents=True, exist_ok=True)
    # Save progress after each question. An interrupted run is never labelled complete.
    with (output / "runs.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            started = time.perf_counter()
            query = question_text(row)
            item: dict[str, Any] = {
                "id": row["QUESTION_ID"],
                "answerable": row["ANSWERABLE"] == "Y",
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
                    ("dense_hash", d[:10], dt),
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
        "questions": len(rows),
        "answerable": len(answerable),
        "semantic_reranker": semantic,
        "dense_embedding": "hash-sha256-384-v1",
        "protocol": "open retrieval over entire corpus; official DOC_IDS not supplied; "
        "N labels refer to official candidate pools, not proof of absence in full corpus",
        "error_count": sum(bool(r["error"]) for r in observations),
        "modes": {},
    }
    for mode in ["dense_hash", "bm25", "dense_rerank", "hybrid_rerank"]:
        summary["modes"][mode] = {
            key: sum(float(r["modes"].get(mode, {}).get(key) or 0) for r in answerable)
            / max(len(answerable), 1)
            for key in ["hit_at_5", "hit_at_10", "mrr", "context_precision_at_5"]
        }
        summary["modes"][mode]["average_latency_ms"] = sum(
            float(r["modes"].get(mode, {}).get("latency_ms", r["latency_ms"])) for r in observations
        ) / max(len(observations), 1)
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["train", "dev", "validation"], default="dev")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--lexical", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "evals/techqa_full")
    args = parser.parse_args()
    result = asyncio.run(evaluate(args.split, args.limit, not args.lexical, args.output))
    LOGGER.info("TechQA summary: %s", result)
    return int(bool(result["error_count"]))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    raise SystemExit(main())
