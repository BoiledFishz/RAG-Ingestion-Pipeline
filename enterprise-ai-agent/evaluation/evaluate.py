"""Evaluate the Agent against every official IBM TechQA development question."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from rag.techqa.metrics import body_token_f1

from agents.rag_agent.factory import build_agent, open_store
from models.schemas import QueryRequest
from models.settings import PROJECT_ROOT, Settings

LOGGER = logging.getLogger(__name__)
DEV_PATH = (
    PROJECT_ROOT / "data" / "techqa" / "extracted" / "TechQA" / "training_and_dev" / "dev_Q_A.json"
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


def checkpoint_protocol(settings: Settings, dev_path: Path) -> dict[str, Any]:
    code = hashlib.sha256()
    for directory in (PROJECT_ROOT / "agents", PROJECT_ROOT / "models",
                      PROJECT_ROOT / "tools", PROJECT_ROOT / "evaluation",
                      PROJECT_ROOT.parent / "src" / "rag"):
        for path in sorted(directory.rglob("*.py")):
            code.update(str(path.relative_to(PROJECT_ROOT.parent)).encode())
            code.update(path.read_bytes())
    calibration = PROJECT_ROOT.parent / "config/techqa_thresholds.json"
    return {
        "dataset_sha256": hashlib.sha256(dev_path.read_bytes()).hexdigest(),
        "settings": settings.model_dump(mode="json", exclude={"qdrant_api_key"}),
        "dense_backend": os.getenv("TECHQA_DENSE_BACKEND", "semantic"),
        "reranker": os.getenv("TECHQA_RERANKER", "nomic"),
        "code_sha256": code.hexdigest(),
        "thresholds_sha256": hashlib.sha256(calibration.read_bytes()).hexdigest(),
    }


async def evaluate(
    settings: Settings, dev_path: Path = DEV_PATH, checkpoint: Path | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    rows = json.loads(await asyncio.to_thread(dev_path.read_text, encoding="utf-8"))
    previous: dict[str, dict[str, Any]] = {}
    reused = 0
    if resume and checkpoint is None:
        raise ValueError("Resume requires a checkpoint directory")
    if checkpoint:
        await asyncio.to_thread(checkpoint.mkdir, parents=True, exist_ok=True)
        protocol = await asyncio.to_thread(checkpoint_protocol, settings, dev_path)
        configuration = checkpoint / "run_config.json"
        if resume:
            if json.loads(configuration.read_text(encoding="utf-8")) != protocol:
                raise ValueError(
                    "Checkpoint dataset, model, code or retrieval configuration changed",
                )
            progress = checkpoint / "progress.jsonl"
            if progress.exists():
                for line in progress.read_text(encoding="utf-8").splitlines():
                    item = json.loads(line)
                    previous[item["question_id"]] = item
        else:
            configuration.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
            (checkpoint / "progress.jsonl").write_text("", encoding="utf-8")
    store = open_store(settings)
    # Top-10 metrics must measure the same candidates the actual agent consumed.
    # One rewrite/retrieval pass per question, with this explicit evaluation budget.
    evaluation_settings = settings.model_copy(update={"top_k": max(settings.top_k, 10)})
    agent = build_agent(evaluation_settings, store)
    results: list[dict[str, Any]] = []
    try:
        for row in rows:
            saved = previous.get(row["QUESTION_ID"])
            if saved is not None and not saved["error"]:
                results.append(saved)
                reused += 1
                continue
            query = question_text(row)
            expected = {str(row["DOCUMENT"])} if row.get("ANSWERABLE") == "Y" else set()
            started = time.perf_counter()
            try:
                run = await agent.run(QueryRequest(query=query))
                ids = run.trace.candidate_ids
                results.append(
                    {
                        "question_id": row["QUESTION_ID"],
                        "answerable": row.get("ANSWERABLE") == "Y",
                        "expected_document": row.get("DOCUMENT"),
                        "hit_at_5": hit_at_k(ids, expected, 5) if expected else None,
                        "hit_at_10": hit_at_k(ids, expected, 10) if expected else None,
                        "mrr": reciprocal_rank(ids, expected) if expected else None,
                        "refused": run.trace.status == "unanswerable",
                        "answered": bool(run.response.sources),
                        "latency_ms": (time.perf_counter() - started) * 1000,
                        "response": run.response.model_dump(),
                        "trace": run.trace.model_dump(),
                        "answer_quality": (
                            body_token_f1(run.response.answer, str(row.get("ANSWER") or ""))
                            * any(s.source_file == f"techqa://{row['DOCUMENT']}"
                                  and f"[{s.source_id}]" in run.response.answer
                                  for s in run.response.sources)
                            if expected else None
                        ),
                        "error": None,
                    }
                )
            except Exception as exc:
                LOGGER.exception("TechQA evaluation failed for %s", row.get("QUESTION_ID"))
                results.append(
                    {
                        "question_id": row.get("QUESTION_ID"),
                        "error": type(exc).__name__,
                        "answerable": row.get("ANSWERABLE") == "Y",
                        "expected_document": row.get("DOCUMENT"),
                        "hit_at_5": 0.0 if expected else None,
                        "hit_at_10": 0.0 if expected else None,
                        "mrr": 0.0 if expected else None,
                        "refused": False,  # An exception is not a successful refusal.
                        "answered": False,
                        "latency_ms": (time.perf_counter() - started) * 1000,
                        "response": None,
                        "answer_quality": 0.0 if expected else None,
                    }
                )
            if checkpoint:
                with (checkpoint / "progress.jsonl").open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(results[-1], ensure_ascii=False) + "\n")
            LOGGER.info("%s completed (%d/%d) error=%s", row["QUESTION_ID"],
                        len(results), len(rows), results[-1]["error"])
    finally:
        if store is not None:
            await store.close()
    successful = [row for row in results if not row["error"]]
    answerable = [row for row in results if row["answerable"]]
    unanswerable = [row for row in results if not row["answerable"]]
    return {
        "summary": {
            "dataset": "IBM TechQA official dev_Q_A.json",
            "collection": (
                os.getenv("TECHQA_DENSE_BACKEND", "semantic")
                if settings.retrieval_backend == "techqa"
                else settings.collection
            ),
            "retrieval_backend": settings.retrieval_backend,
            "protocol": "open full-corpus retrieval; N labels concern official DOC_IDS only",
            "profile": settings.profile,
            "model": settings.model if settings.profile == "ollama" else None,
            "evaluation_top_k": evaluation_settings.top_k,
            "answer_quality_method": "answer-body token F1 multiplied by correct document citation",
            "question_count": len(results),
            "complete": len(results) == len(rows),
            "resumed": resume,
            "reused_questions": reused,
            "answerable_count": len(answerable),
            "unanswerable_count": len(unanswerable),
            "hit_at_5": average([row["hit_at_5"] for row in answerable]),
            "hit_at_10": average([row["hit_at_10"] for row in answerable]),
            "mrr": average([row["mrr"] for row in answerable]),
            "unanswerable_refusal_accuracy": average(
                [float(row["refused"]) for row in unanswerable]
            ),
            "answer_quality": average([float(row["answer_quality"] or 0) for row in answerable]),
            "answerable_acceptance": average([float(row["answered"]) for row in answerable]),
            "average_latency_ms": average([row["latency_ms"] for row in results]),
            "error_count": len(results) - len(successful),
        },
        "rows": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "evaluation" / "results")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(evaluate(Settings.from_env(), checkpoint=args.output, resume=args.resume))
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
