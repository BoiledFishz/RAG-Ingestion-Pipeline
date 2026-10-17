"""Chap12 comparison on the mixed task set: Project 1 baseline, single RAG agent, Multi-Agent.

    python -m evaluation.chap12_eval --split sample --output evaluation/results/chap12/<name>
    python -m evaluation.chap12_eval ... --repeats 3 --limit-per-type 30 --resume

Systems (same index, same model and budget limits):
  p1_single  Project 1 configuration on the sample: BM25 only, Project 1 reranker
             (lexical offline / nomic with Ollama) and Project 1 acceptance threshold.
  single     The current RAG Worker configuration alone (no Supervisor, no data capability).
  multi      Chap12 Supervisor-Worker.
Gold is read only for scoring, after each run. Every failure stays in the denominator.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import statistics
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from rag.techqa.data import ROOT

from agents.chap12.budget import Budget, metered
from agents.chap12.contracts import AnalysisRequest, TrustedContext
from agents.chap12.factory import budget_limits, build_rag_agent, build_supervisor
from agents.chap12.rag_worker import doc_id
from evaluation.chap12_build_tasks import raw_documents
from evaluation.chap12_compare import token_f1
from models.schemas import QueryRequest
from models.settings import Settings

HERE = Path(__file__).resolve().parent / "chap12"
SYSTEMS = ("p1_single", "single", "multi")
FULL = TrustedContext.model_validate({
    "subject_id": "evaluator", "tenant_id": "course", "allowed_workers": ["rag", "database"],
    "allowed_db_operations": ["count_documents", "count_by_year", "list_recent_documents",
                              "search_product_documents"],
    "allowed_product_ids": ["*"]})


def git_commit() -> str:
    try:
        return subprocess.run(["git", "-c", "safe.directory=*", "rev-parse", "HEAD"],
                              capture_output=True, text=True, cwd=ROOT, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def usage_of(budget: Budget, started: float) -> dict[str, Any]:
    return {"llm_calls": budget.used["llm"], "embedding_calls": budget.used["embedding"],
            "embedding_cache_hits": budget.embedding_cache_hits, "sql": budget.used["sql"],
            "local": budget.used["local"], "db_queries": budget.used["db"],
            "prompt_tokens": budget.prompt_tokens, "completion_tokens": budget.completion_tokens,
            "latency_ms": (time.monotonic() - started) * 1000}


async def run_single(agent: Any, task: dict[str, Any]) -> dict[str, Any]:
    budget, started = Budget(budget_limits()), time.monotonic()
    out: dict[str, Any] = {"data_status": "unsupported"}
    try:
        with metered(budget, "rag"):
            run = await asyncio.wait_for(agent.run(QueryRequest(query=task["query"][:2000])),
                                         timeout=budget.limits.deadline_seconds)
        published = bool(run.response.sources)
        out |= {"rag_status": run.trace.status, "published": published,
                "answer": run.response.answer if published else "",
                "cited": [doc_id(s.source_file) for s in run.response.sources],
                "retrieved": list(dict.fromkeys(doc_id(c) for c in run.trace.candidate_ids)),
                "error": None}
        # A single agent cannot produce the data part of data / explain_and_data tasks.
        part = "completed" if published and run.trace.status == "answered" else (
            "partial" if published else "no_data")
        out["status"] = part if task["type"] == "explain" else (
            "partial" if published else "no_data")
    except Exception as exc:  # recorded, stays in the denominator
        out |= {"status": "timeout" if isinstance(exc, TimeoutError) else "failed",
                "rag_status": None, "published": False, "answer": "", "cited": [],
                "retrieved": [], "error": type(exc).__name__}
    return out | usage_of(budget, started)


async def run_multi(supervisor: Any, task: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    out: dict[str, Any] = {}
    try:
        request = AnalysisRequest.model_validate({k: task[k] for k in ("query", "goal",
                                                                       "data_request")
                                                  if k in task} | {"query": task["query"][:4000]})
        result = await supervisor.run(request, FULL)
        by_worker = {w.worker: w for w in result.worker_results}
        rag, db = by_worker.get("rag"), by_worker.get("database")
        published = rag is not None and rag.status in {"completed", "partial"}
        payload = result.data_result
        out |= {"status": result.status,
                "rag_status": getattr(rag.payload, "rag_status", None) if rag else None,
                "published": published,
                "answer": getattr(rag.payload, "answer", "") if published and rag else "",
                "cited": [c.doc_id for c in result.citations] if published else [],
                "retrieved": getattr(rag.payload, "retrieved_doc_ids", []) if rag else [],
                "data_status": db.status if db else None,
                "data_error": db.error.category if db and db.error else None,
                "data": None if payload is None else {
                    "operation": payload.operation, "product_id": payload.product_id,
                    "product_source": payload.product_source, "count": payload.count,
                    "rows": [[r.key, r.value] for r in payload.rows],
                    "date_from": payload.date_from, "doc_class": payload.doc_class},
                "error": rag.error.category if rag and rag.error else None,
                "llm_calls": result.usage.llm_calls, "embedding_calls":
                result.usage.embedding_calls, "embedding_cache_hits":
                result.usage.embedding_cache_hits, "sql": result.usage.sql_statements,
                "local": result.usage.local_compute, "db_queries": result.usage.db_queries,
                "prompt_tokens": result.usage.prompt_tokens,
                "completion_tokens": result.usage.completion_tokens}
    except Exception as exc:
        out |= {"status": "failed", "published": False, "answer": "", "cited": [],
                "retrieved": [], "data_status": "failed", "error": type(exc).__name__}
    out["latency_ms"] = (time.monotonic() - started) * 1000
    return out


class Scorer:
    def __init__(self, index: Path, gold: dict[str, dict[str, Any]]) -> None:
        self.gold = gold
        self.docs = raw_documents(index)
        self.by_product: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for d in self.docs:
            for pid in d["ids"]:
                self.by_product[pid].append(d)
        self.products_of = {d["doc_id"]: d["ids"] for d in self.docs}

    def pool(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        return [d for d in self.by_product.get(str(data["product_id"]), [])
                if (not data.get("doc_class") or d["class"] == data["doc_class"])
                and (not data.get("date_from") or (d["date"] and d["date"] >= data["date_from"]))]

    def verify(self, data: dict[str, Any]) -> bool:
        """Independent check of a DB payload against raw metadata."""
        if data["operation"] == "search_product_documents":
            # Ranking is BM25 (not recomputed); every row must satisfy the product/filters.
            allowed = {d["doc_id"] for d in self.pool(data)}
            rows = self.observed(data)
            return len(rows) == len(set(rows)) and set(rows) <= allowed
        return bool(self.observed(data) == self.recount(data))

    def recount(self, data: dict[str, Any]) -> Any:
        """Independent recomputation of a DB payload from raw metadata."""
        pool = self.pool(data)
        if data["operation"] == "count_documents":
            return len(pool)
        if data["operation"] == "count_by_year":
            return dict(sorted(Counter(d["date"][:4] for d in pool if d["date"]).items()))
        ordered = sorted(pool, key=lambda d: d["doc_id"])
        ordered.sort(key=lambda d: d["date"] or "", reverse=True)
        return [d["doc_id"] for d in ordered[:len(data["rows"]) or 5]]

    @staticmethod
    def observed(data: dict[str, Any]) -> Any:
        if data["operation"] == "count_documents":
            return data["count"]
        if data["operation"] == "count_by_year":
            return {str(k): int(v) for k, v in data["rows"]}
        return [k for k, _ in data["rows"]]

    def score(self, task: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
        gold = self.gold[task["task_id"]]
        s: dict[str, Any] = {}
        if task["type"] in {"explain", "explain_and_data"}:
            y = gold["answerable"] == "Y"
            s["answerable"] = y
            if y:
                rank = (record["retrieved"].index(gold["document"]) + 1
                        if gold["document"] in record["retrieved"] else None)
                s |= {"y_accept": record["published"],
                      "gold_cited": gold["document"] in record["cited"], "gold_rank": rank,
                      "token_f1": token_f1(record["answer"], gold["answer"])
                      if record["published"] else 0.0}
                rag_ok = s["gold_cited"]
            else:
                s["n_refuse"] = not record["published"]
                rag_ok = s["n_refuse"]
            s["rag_correct"] = rag_ok
        data = record.get("data")
        if task["type"] == "data":
            if data is None:
                s["data_correct"] = False
            elif task["data_request"]["operation"] == "count_documents":
                s["data_correct"] = data["count"] == gold["count"]
            elif task["data_request"]["operation"] == "count_by_year":
                s["data_correct"] = self.observed(data) == gold["by_year"]
            else:
                s["data_correct"] = self.observed(data) == gold["rows"]
            s["correct"] = s["data_correct"]
        elif task["type"] == "explain_and_data":
            if data is None:
                s["data_correct"] = False
            else:
                s["data_correct"] = self.verify(data)
                if gold["answerable"] == "Y":
                    s["product_matches_gold_doc"] = data["product_id"] in self.products_of.get(
                        gold["document"], set())
                    s["related_contains_gold"] = gold["document"] in self.observed(data) if \
                        data["operation"] in {"list_recent_documents",
                                              "search_product_documents"} else False
            product_ok = s.get("product_matches_gold_doc", True)
            s["correct"] = bool(s["rag_correct"] and s["data_correct"] and product_ok)
        else:
            s["correct"] = s["rag_correct"]
        return s


def bootstrap(per_task: list[float], draws: int = 2000, seed: int = 0) -> list[float] | None:
    if not per_task:
        return None
    rng = random.Random(seed)
    n = len(per_task)
    means = sorted(statistics.fmean(rng.choices(per_task, k=n)) for _ in range(draws))
    return [round(means[int(0.025 * draws)], 4), round(means[int(0.975 * draws) - 1], 4)]


def metric(rows: list[dict[str, Any]], key: str, source: str = "score") -> dict[str, Any]:
    """Mean over tasks of the per-task mean over repeats; 95% CI: task-level bootstrap."""
    per: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        value = (r["score"] if source == "score" else r).get(key)
        if value is None:
            continue
        per[r["task_id"]].append(float(value))
    values = [statistics.fmean(v) for v in per.values()]
    if not values:
        return {"n_tasks": 0, "mean": None, "ci95": None}
    return {"n_tasks": len(values), "mean": round(statistics.fmean(values), 4),
            "ci95": bootstrap(values)}


def balanced(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ys = metric(rows, "y_accept")
    ns = metric(rows, "n_refuse")
    if ys["mean"] is None or ns["mean"] is None:
        return {"mean": None}
    per_y = defaultdict(list)
    per_n = defaultdict(list)
    for r in rows:
        if "y_accept" in r["score"]:
            per_y[r["task_id"]].append(float(r["score"]["y_accept"]))
        if "n_refuse" in r["score"]:
            per_n[r["task_id"]].append(float(r["score"]["n_refuse"]))
    yv = [statistics.fmean(v) for v in per_y.values()]
    nv = [statistics.fmean(v) for v in per_n.values()]
    rng = random.Random(1)
    draws = sorted((statistics.fmean(rng.choices(yv, k=len(yv)))
                    + statistics.fmean(rng.choices(nv, k=len(nv)))) / 2 for _ in range(2000))
    return {"mean": round((ys["mean"] + ns["mean"]) / 2, 4),
            "ci95": [round(draws[50], 4), round(draws[1949], 4)],
            "y_tasks": len(yv), "n_tasks": len(nv)}


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for system in [s for s in SYSTEMS if any(r["system"] == s for r in records)]:
        out[system] = {}
        for kind in ("explain", "explain_and_data", "data", "all"):
            rows = [r for r in records if r["system"] == system
                    and (kind == "all" or r["type"] == kind)]
            if not rows:
                continue
            latencies = sorted(r["latency_ms"] for r in rows)
            ranks = [r["score"].get("gold_rank") for r in rows if "gold_rank" in r["score"]]
            block: dict[str, Any] = {
                "records": len(rows), "tasks": len({r["task_id"] for r in rows}),
                "status_counts": dict(Counter(r["status"] for r in rows)),
                "complete_rate (status=completed; includes wrong N publications)":
                    metric([{**r, "score": {"c": r["status"] == "completed"}} for r in rows],
                           "c"),
                "correct_completion": metric(rows, "correct"),
                "failure_rate (failed+timeout)": metric(
                    [{**r, "score": {"f": r["status"] in {"failed", "timeout"}}} for r in rows],
                    "f"),
                "latency_ms": {"mean": round(statistics.fmean(latencies), 1),
                               "p50": round(latencies[len(latencies) // 2], 1),
                               "p95": round(latencies[max(0, int(0.95 * len(latencies)) - 1)],
                                            1)},
            }
            for key in ("llm_calls", "embedding_calls", "embedding_cache_hits", "sql", "local",
                        "db_queries", "prompt_tokens", "completion_tokens"):
                block[f"{key}_mean"] = metric(rows, key, source="record")["mean"]
            if kind in {"explain", "explain_and_data", "all"}:
                block |= {"rag_correct": metric(rows, "rag_correct"),
                          "y_accept": metric(rows, "y_accept"),
                          "n_refuse": metric(rows, "n_refuse"),
                          "balanced_accuracy": balanced(rows),
                          "y_gold_cited": metric(rows, "gold_cited"),
                          "y_token_f1": metric(rows, "token_f1")}
                if ranks:
                    block["retrieval_y"] = {
                        **{f"R@{k}": round(sum(1 for x in ranks if x and x <= k) / len(ranks), 4)
                           for k in (1, 3, 5, 8)},
                        "MRR": round(sum(1 / x for x in ranks if x) / len(ranks), 4),
                        "observations": len(ranks)}
            if kind in {"data", "explain_and_data", "all"}:
                block |= {"data_correct": metric(rows, "data_correct"),
                          "data_status_counts": dict(Counter(str(r.get("data_status"))
                                                             for r in rows))}
            if kind in {"explain_and_data", "all"}:
                block |= {"product_matches_gold_doc": metric(rows, "product_matches_gold_doc"),
                          "related_docs_contain_gold": metric(rows, "related_contains_gold")}
            out[system][kind] = block
    return out


async def main_async(args: argparse.Namespace) -> None:
    settings = Settings.from_env()
    folder = HERE if args.split == "sample" else HERE / args.split
    index = ROOT / f".rag_data/chap12_{args.split}.sqlite"
    os.environ["CHAP12_INDEX_PATH"] = str(index)
    tasks = [json.loads(x) for x in (folder / "mixed_tasks.jsonl").read_text("utf-8")
             .splitlines()]
    if args.limit_per_type:
        seen: Counter[str] = Counter()
        kept = []
        for task in tasks:  # file order is random within type: a prefix is a random subset
            if seen[task["type"]] < args.limit_per_type:
                kept.append(task)
                seen[task["type"]] += 1
        tasks = kept
    gold = {g["task_id"]: g for g in map(json.loads, (folder / "mixed_gold.jsonl")
                                         .read_text("utf-8").splitlines())}
    args.output.mkdir(parents=True, exist_ok=True)
    runs = args.output / "runs.jsonl"
    if runs.exists() and not args.resume:
        raise FileExistsError(f"{runs} exists; use --resume or a new --output")
    done = {(r["system"], r["task_id"], r["repeat"]) for r in map(
        json.loads, runs.read_text("utf-8").splitlines())} if runs.exists() else set()
    from tools.sample_retriever import SampleRetrieverTool

    p1_rerank = "lexical" if settings.profile == "offline" else "nomic"
    agents = {
        "p1_single": build_rag_agent(settings, index, SampleRetrieverTool(
            index, use_dense=False, rerank=p1_rerank, use_calibration=False)),
        "single": build_rag_agent(settings, index),
    }
    supervisor = build_supervisor(settings, index)
    systems = [s for s in args.systems.split(",") if s]
    scorer = Scorer(index, gold)
    with runs.open("a", encoding="utf-8") as handle:
        for repeat in range(1, args.repeats + 1):
            for number, task in enumerate(tasks, 1):
                # Rotate system order per task so no system always runs on a warm cache.
                shift = (number + repeat) % len(systems)
                for system in systems[shift:] + systems[:shift]:
                    if (system, task["task_id"], repeat) in done:
                        continue
                    record = await (run_multi(supervisor, task) if system == "multi"
                                    else run_single(agents[system], task))
                    record |= {"system": system, "task_id": task["task_id"],
                               "type": task["type"], "repeat": repeat}
                    record["score"] = scorer.score(task, record)
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                    handle.flush()
                print(f"repeat {repeat} {number}/{len(tasks)} {task['task_id']}", flush=True)
    records = [json.loads(x) for x in runs.read_text("utf-8").splitlines()]
    meta = json.loads(args.meta.read_text("utf-8")) if args.meta else {}
    summary = {
        "split": args.split, "profile": settings.profile,
        "model": settings.model if settings.profile == "ollama" else None,
        "reranker": {"p1_single": p1_rerank, "single/multi": os.getenv(
            "CHAP12_RERANKER", "minilm" if settings.profile == "offline" else "nomic")},
        "gap_gate_env": os.getenv("CHAP12_GAP_GATE"), "repeats": args.repeats,
        "limit_per_type": args.limit_per_type, "budget": budget_limits().model_dump(),
        "git_commit": git_commit(), "run_metadata": meta,
        "tasks_file_sha256": __import__("hashlib").sha256(
            (folder / "mixed_tasks.jsonl").read_bytes()).hexdigest(),
        "ci_method": "task-level percentile bootstrap (2000 draws) of per-task means over "
                     "repeats",
        "system_order": "rotated per task and repeat (cache warm-up is not system-specific)",
        "systems": summarize(records),
    }
    (args.output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1)
                                              + "\n", "utf-8")
    print(json.dumps({s: {k: v.get("correct_completion") for k, v in b.items()}
                      for s, b in summary["systems"].items()}, ensure_ascii=False, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["sample", "confirm", "tune"], default="sample")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--limit-per-type", type=int, default=0)
    parser.add_argument("--systems", default=",".join(SYSTEMS))
    parser.add_argument("--meta", type=Path, default=None,
                        help="JSON with run metadata (model digests, versions)")
    parser.add_argument("--resume", action="store_true")
    asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    main()
