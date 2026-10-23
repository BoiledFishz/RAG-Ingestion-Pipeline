"""Fixed-sample comparison: single RAG agent (Project 1) vs Chap12 Supervisor-Worker.

Usage (from enterprise-ai-agent, PYTHONPATH=../src;.):
    $env:AGENT_PROFILE="ollama"
    python -m evaluation.chap12_compare --output evaluation/chap12/results/ollama_run1
    python -m evaluation.chap12_compare --output ... --resume      # continue after interruption

Both systems use the same sample index, retriever, thresholds, model and budget limits.
Gold answers are read only here, after each run, for scoring; they never reach either system.
Every failure stays in the denominator.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import sqlite3
import statistics
import time
from pathlib import Path
from typing import Any

from agents.chap12.budget import Budget, metered
from agents.chap12.contracts import AnalysisRequest, TrustedContext
from agents.chap12.factory import budget_limits, build_rag_agent, build_supervisor, index_path
from agents.chap12.rag_worker import doc_id
from models.schemas import QueryRequest
from models.settings import Settings

TASKS = Path(__file__).resolve().parent / "chap12/tasks.jsonl"
GOLD = Path(__file__).resolve().parent / "chap12/gold.jsonl"
FULL_ACCESS = TrustedContext.model_validate({
    "subject_id": "evaluator", "tenant_id": "course", "allowed_workers": ["rag", "database"],
    "allowed_db_operations": ["count_documents", "count_by_year", "list_recent_documents"],
    "allowed_product_ids": ["*"]})


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold())


def token_f1(prediction: str, gold: str) -> float:
    p, g = tokens(prediction), tokens(gold)
    if not p or not g:
        return 0.0
    common = sum(min(p.count(t), g.count(t)) for t in set(p) & set(g))
    if common == 0:
        return 0.0
    precision, recall = common / len(p), common / len(g)
    return 2 * precision * recall / (precision + recall)


def wilson(successes: int, n: int) -> list[float] | None:
    if n == 0:
        return None
    z, phat = 1.959964, successes / n
    centre = (phat + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)]


def independent_count(db: sqlite3.Connection, product_id: str) -> int:
    """Recount from raw metadata JSON, not from the Worker's derived tables."""
    total = 0
    for (raw,) in db.execute("SELECT metadata FROM docs"):
        ids = {p.strip() for p in str(json.loads(raw).get("productId") or "").split(",")}
        total += product_id in ids
    return total


async def run_single(agent: Any, task: dict[str, Any]) -> dict[str, Any]:
    budget = Budget(budget_limits())
    started = time.monotonic()
    record: dict[str, Any] = {"system": "single_agent", "task_id": task["task_id"]}
    try:
        with metered(budget, "rag"):
            run = await asyncio.wait_for(agent.run(QueryRequest(query=task["query"])),
                                         timeout=budget.limits.deadline_seconds)
        published = bool(run.response.sources)
        part = ("completed" if published and run.trace.status == "answered" else
                "partial" if published else "no_data")
        record |= {
            # The task also asks for data, which a single RAG agent cannot supply.
            "status": "partial" if published else part, "rag_part_status": part,
            "rag_status": run.trace.status, "answer": run.response.answer if published else "",
            "cited": [doc_id(s.source_file) for s in run.response.sources],
            "retrieved": list(dict.fromkeys(doc_id(c) for c in run.trace.candidate_ids)),
            "data_status": "unsupported", "error": None,
        }
    except Exception as exc:  # every failure is recorded and stays in the denominator
        failed = "timeout" if isinstance(exc, TimeoutError) else "failed"
        record |= {"status": failed, "rag_part_status": failed,
                   "rag_status": None, "answer": "", "cited": [], "retrieved": [],
                   "data_status": "unsupported", "error": type(exc).__name__}
    record |= {"latency_ms": (time.monotonic() - started) * 1000,
               "llm_calls": budget.used["llm"], "embedding_calls": budget.used["embedding"],
               "db_queries": 0}
    return record


async def run_multi(supervisor: Any, task: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    record: dict[str, Any] = {"system": "multi_agent", "task_id": task["task_id"]}
    try:
        result = await supervisor.run(AnalysisRequest(query=task["query"]), FULL_ACCESS)
        rag, db = result.worker_results
        rag_payload = rag.payload
        published = rag.status in {"completed", "partial"}
        record |= {
            "status": result.status, "rag_part_status": rag.status,
            "rag_status": getattr(rag_payload, "rag_status", None),
            "answer": getattr(rag_payload, "answer", "") if published else "",
            "cited": [c.doc_id for c in result.citations] if published else [],
            "retrieved": getattr(rag_payload, "retrieved_doc_ids", []),
            "data_status": db.status, "data_error": db.error.category if db.error else None,
            "data_product": result.data_result.product_id if result.data_result else None,
            "data_product_source": (result.data_result.product_source if result.data_result
                                    else None),
            "data_count": result.data_result.count if result.data_result else None,
            "error": rag.error.category if rag.error else None,
            "llm_calls": result.usage.llm_calls, "embedding_calls": result.usage.embedding_calls,
            "db_queries": result.usage.db_queries,
        }
    except Exception as exc:
        record |= {"status": "failed", "rag_part_status": "failed", "answer": "", "cited": [],
                   "retrieved": [],
                   "data_status": "failed", "error": type(exc).__name__, "llm_calls": None,
                   "embedding_calls": None, "db_queries": None}
    record["latency_ms"] = (time.monotonic() - started) * 1000
    return record


def gold_products(db: sqlite3.Connection, doc: str) -> set[str]:
    row = db.execute("SELECT metadata FROM docs WHERE doc_id=?", (doc,)).fetchone()
    raw = json.loads(row[0]).get("productId") if row else ""
    return {p.strip() for p in str(raw or "").split(",") if p.strip()}


def score(record: dict[str, Any], gold: dict[str, Any], db: sqlite3.Connection) -> dict[str, Any]:
    answerable = gold["answerable"] == "Y"
    published = bool(record["cited"])
    out: dict[str, Any] = {"answerable": answerable, "published": published}
    if answerable:
        retrieved = record["retrieved"]
        rank = retrieved.index(gold["document"]) + 1 if gold["document"] in retrieved else None
        out |= {"gold_cited": gold["document"] in record["cited"],
                "gold_retrieved": rank is not None, "gold_rank": rank,
                "token_f1": token_f1(record["answer"], gold["answer"]) if published else 0.0}
        if record.get("data_product"):
            # Proxy only: the product tagged on the official answer document.
            out["data_product_matches_gold_doc"] = record["data_product"] in gold_products(
                db, gold["document"])
    else:
        out["refused"] = not published
    if record.get("data_count") is not None and record.get("data_product"):
        out["data_correct"] = record["data_count"] == independent_count(db, record["data_product"])
    return out


def counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    output: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key))
        output[value] = output.get(value, 0) + 1
    return output


def recall(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Document-level gold recall of the RAG candidates (order = agent candidate order)."""
    ranks = [r["score"].get("gold_rank") for r in rows if r["score"]["answerable"]]
    n = len(ranks)
    output: dict[str, Any] = {"denominator": n}
    if not n:
        return output
    for k in (1, 3, 5, 8):
        hits = sum(1 for x in ranks if x is not None and x <= k)
        output[f"R@{k}"] = {"value": round(hits / n, 4), "hits": hits, "wilson95": wilson(hits, n)}
    output["MRR"] = round(sum(1 / x for x in ranks if x) / n, 4)
    return output


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    def rate(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
        values = [r["score"][key] for r in rows if key in r["score"]]
        hits = sum(bool(v) for v in values)
        return {"numerator": hits, "denominator": len(values),
                "value": round(hits / len(values), 4) if values else None,
                "wilson95": wilson(hits, len(values))}

    def mean(rows: list[dict[str, Any]], key: str, scored: bool = False) -> float | None:
        values = [(r["score"] if scored else r).get(key) for r in rows]
        numbers = [float(v) for v in values if v is not None]
        return round(statistics.fmean(numbers), 4) if numbers else None

    output: dict[str, Any] = {}
    for system in sorted({r["system"] for r in records}):
        rows = [r for r in records if r["system"] == system]
        latencies = sorted(r["latency_ms"] for r in rows)
        statuses: dict[str, int] = {}
        for row in rows:
            statuses[row["status"]] = statuses.get(row["status"], 0) + 1
        data_statuses: dict[str, int] = {}
        rag_parts: dict[str, int] = {}
        for row in rows:
            data_statuses[row["data_status"]] = data_statuses.get(row["data_status"], 0) + 1
            rag_parts[row["rag_part_status"]] = rag_parts.get(row["rag_part_status"], 0) + 1
        failures = sum(r["status"] in {"failed", "timeout"} for r in rows)
        output[system] = {
            "tasks": len(rows), "status_counts": statuses, "data_status_counts": data_statuses,
            "rag_part_status_counts": rag_parts,
            "complete_rate": rate([{**r, "score": {"c": r["status"] == "completed"}}
                                   for r in rows], "c"),
            "failure_rate": {"numerator": failures, "denominator": len(rows),
                             "wilson95": wilson(failures, len(rows))},
            "Y_answer_published": rate([r for r in rows if r["score"]["answerable"]],
                                       "published"),
            "Y_gold_doc_cited": rate(rows, "gold_cited"),
            "Y_gold_doc_retrieved": rate(rows, "gold_retrieved"),
            "Y_token_f1_mean": mean([r for r in rows if r["score"]["answerable"]], "token_f1",
                                    True),
            "N_refused": rate(rows, "refused"),
            "retrieval_Y": recall(rows),
            "data_product_source_counts": counts(rows, "data_product_source"),
            "data_product_matches_gold_doc": rate(rows, "data_product_matches_gold_doc"),
            "data_product_matches_gold_doc_by_source": {
                source: rate([r for r in rows if r.get("data_product_source") == source],
                             "data_product_matches_gold_doc")
                for source in ("query_literal", "inferred", "explicit")},
            "data_result_correct": rate(rows, "data_correct"),
            "latency_ms": {"mean": round(statistics.fmean(latencies), 1),
                           "p50": round(latencies[len(latencies) // 2], 1),
                           "p95": round(latencies[math.ceil(0.95 * len(latencies)) - 1], 1)},
            "llm_calls_mean": mean(rows, "llm_calls"),
            "embedding_calls_mean": mean(rows, "embedding_calls"),
            "db_queries_mean": mean(rows, "db_queries"),
            "tokens": None,
        }
    return output


async def main_async(args: argparse.Namespace) -> None:
    settings = Settings.from_env()
    tasks = [json.loads(line) for line in TASKS.read_text(encoding="utf-8").splitlines()]
    tasks = tasks[: args.limit] if args.limit else tasks
    gold = {g["task_id"]: g for g in map(json.loads,
                                         GOLD.read_text(encoding="utf-8").splitlines())}
    args.output.mkdir(parents=True, exist_ok=True)
    runs = args.output / "runs.jsonl"
    if runs.exists() and not args.resume:
        raise FileExistsError(f"{runs} exists; use --resume or a new --output")
    done = {(r["system"], r["task_id"]) for r in map(json.loads, runs.read_text(
        encoding="utf-8").splitlines())} if runs.exists() else set()
    path = index_path()
    agent, supervisor = build_rag_agent(settings, path), build_supervisor(settings, path)
    raw = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    with runs.open("a", encoding="utf-8") as handle:
        for number, task in enumerate(tasks, 1):
            for system in ("single_agent", "multi_agent"):
                if (system, task["task_id"]) in done:
                    continue
                record = await (run_single(agent, task) if system == "single_agent"
                                else run_multi(supervisor, task))
                record["score"] = score(record, gold[task["task_id"]], raw)
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
            print(f"{number}/{len(tasks)} {task['task_id']}", flush=True)
    records = [json.loads(line) for line in runs.read_text(encoding="utf-8").splitlines()]
    summary = {
        "profile": settings.profile, "model": settings.model if settings.profile == "ollama"
        else "none (rule rewrite + extractive selection)",
        "sample": json.loads((TASKS.parent / "sample_manifest.json").read_text(
            encoding="utf-8"))["scope"],
        "index": str(path.name), "budget": budget_limits().model_dump(),
        "systems": summarize(records),
        "notes": [
            "single_agent cannot answer the data part of the task: data_status=unsupported.",
            "Token counts are not exposed by the reused Ollama adapter; reported as null.",
            "Retrieval thresholds were calibrated on the training split this sample comes from.",
            "N refusal is a proxy: official N labels refer to the official candidate set only.",
        ],
    }
    (args.output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)
                                              + "\n", encoding="utf-8")
    print(json.dumps(summary["systems"], ensure_ascii=False, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    main()
