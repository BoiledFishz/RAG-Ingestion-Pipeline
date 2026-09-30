"""Evaluate the Agent against every official IBM TechQA development question."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from agents.rag_agent.factory import build_agent, build_embedder, open_store
from models.schemas import QueryRequest, RetrieverInput
from models.settings import PROJECT_ROOT, Settings
from tools.retriever import RetrieverTool

LOGGER = logging.getLogger(__name__)
DEV_PATH = (
    PROJECT_ROOT
    / "data"
    / "techqa"
    / "extracted"
    / "TechQA"
    / "training_and_dev"
    / "dev_Q_A.json"
)


def document_id(chunk_id: str) -> str:
    parts = chunk_id.split(":", 3)
    return parts[1] if len(parts) >= 3 and parts[0] == "techqa" else chunk_id


def hit_at_k(ids: list[str], expected: set[str], k: int = 5) -> float:
    return float(any(document_id(value) in expected for value in ids[:k]))


def reciprocal_rank(ids: list[str], expected: set[str]) -> float:
    return next(
        (1 / rank for rank, value in enumerate(ids, 1) if document_id(value) in expected), 0.0
    )


def question_text(row: dict[str, Any]) -> str:
    title = str(row.get("QUESTION_TITLE") or "").strip()
    body = str(row.get("QUESTION_TEXT") or row.get("QUESTION_BODY") or "").strip()
    return title if not body or body == title else f"{title}\n{body}"


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


async def evaluate(settings: Settings, dev_path: Path = DEV_PATH) -> dict[str, Any]:
    rows = json.loads(await asyncio.to_thread(dev_path.read_text, encoding="utf-8"))
    store = open_store(settings)
    embedder = build_embedder(settings)
    tool = RetrieverTool(store, embedder, settings.tool_timeout)
    agent = build_agent(settings, store)
    results: list[dict[str, Any]] = []
    try:
        for row in rows:
            query = question_text(row)
            expected = {str(row["DOCUMENT"])} if row.get("ANSWERABLE") == "Y" else set()
            started = time.perf_counter()
            try:
                candidates = await tool.invoke(
                    RetrieverInput(query=query, top_k=max(settings.top_k, 10))
                )
                run = await agent.run(QueryRequest(query=query))
                ids = [item.chunk_id for item in candidates]
                results.append(
                    {
                        "question_id": row["QUESTION_ID"],
                        "answerable": row.get("ANSWERABLE") == "Y",
                        "expected_document": row.get("DOCUMENT"),
                        "hit_at_5": hit_at_k(ids, expected, 5) if expected else None,
                        "hit_at_10": hit_at_k(ids, expected, 10) if expected else None,
                        "mrr": reciprocal_rank(ids, expected) if expected else None,
                        "refused": not run.response.sources,
                        "latency_ms": (time.perf_counter() - started) * 1000,
                        "response": run.response.model_dump(),
                        "error": None,
                    }
                )
            except Exception as exc:
                LOGGER.exception("TechQA evaluation failed for %s", row.get("QUESTION_ID"))
                results.append(
                    {
                        "question_id": row.get("QUESTION_ID"), "error": type(exc).__name__,
                        "answerable": row.get("ANSWERABLE") == "Y",
                        "expected_document": row.get("DOCUMENT"),
                        "hit_at_5": 0.0 if expected else None,
                        "hit_at_10": 0.0 if expected else None,
                        "mrr": 0.0 if expected else None,
                        "refused": False,  # An exception is not a successful refusal.
                        "latency_ms": (time.perf_counter() - started) * 1000,
                        "response": None,
                    }
                )
    finally:
        await store.close()
    successful = [row for row in results if not row["error"]]
    answerable = [row for row in results if row["answerable"]]
    unanswerable = [row for row in results if not row["answerable"]]
    return {
        "summary": {
            "dataset": "IBM TechQA official dev_Q_A.json",
            "collection": settings.collection,
            "profile": settings.profile,
            "question_count": len(results),
            "answerable_count": len(answerable),
            "unanswerable_count": len(unanswerable),
            "hit_at_5": average([row["hit_at_5"] for row in answerable]),
            "hit_at_10": average([row["hit_at_10"] for row in answerable]),
            "mrr": average([row["mrr"] for row in answerable]),
            "unanswerable_refusal_accuracy": average(
                [float(row["refused"]) for row in unanswerable]
            ),
            "average_latency_ms": average([row["latency_ms"] for row in results]),
            "error_count": len(results) - len(successful),
        },
        "rows": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "evaluation" / "results")
    args = parser.parse_args()
    result = asyncio.run(evaluate(Settings.from_env()))
    args.output.mkdir(parents=True, exist_ok=True)
    for name, value in (("summary.json", result["summary"]), ("runs.json", result["rows"])):
        (args.output / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    LOGGER.info("TechQA evaluation summary: %s", result["summary"])
    return int(bool(result["summary"]["error_count"]))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    raise SystemExit(main())
