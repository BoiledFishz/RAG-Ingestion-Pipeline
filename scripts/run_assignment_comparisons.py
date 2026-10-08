"""Homework-only tune comparisons; never load or run held-out.

Official answers/labels/targets are read only by the scoring function after a
request returns. Plans and query projections are registered before any request.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT),
    str(ROOT / "scripts"),
    str(ROOT / "src"),
    str(ROOT / "enterprise-ai-agent"),
]
from project2_stage_eval import select_questions  # noqa: E402 -- local CLI path bootstrap
from project2_v031_calibration import HostGuard, digest, save  # noqa: E402

from evaluation_protocol.statistics import metric  # noqa: E402
from evaluation_protocol.storage import query  # noqa: E402

AUDIT = ROOT / "audit/assignment-completion-20261007"
LOGGER = logging.getLogger(__name__)


def lock(folder: Path, tasks: list[dict[str, Any]], mode: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "plan.json"
    if path.exists():
        raise ValueError("Comparison already registered; no selective rerun")
    baseline = ROOT / "evals/protocol_v0/baseline_v0.config.json"
    files = json.loads(baseline.read_text(encoding="utf-8"))["sut"]["files"]
    for name, expected in files.items():
        if digest(ROOT / name) != expected:
            raise ValueError("Frozen baseline changed: " + name)
    save(
        path,
        {
            "mode": mode,
            "partition": "tune",
            "seed": 20261005,
            "repeats": 3,
            "tasks": tasks,
            "baseline_sha256": digest(baseline),
            "online_sources": {
                p.relative_to(ROOT).as_posix(): digest(p)
                for p in (ROOT / "enterprise-ai-agent/agents/project2").glob("*.py")
            },
            "heldout_new_calls": 0,
            "errors_remain_in_denominator": True,
            "cost": None,
            "token_counts": "provider observation when available; no fabricated totals",
            "quality_limit": "body F1 is a proxy, not fact correctness; S14 unchanged",
        },
    )
    path.with_suffix(".json.sha256").write_text(digest(path) + "\n", encoding="utf-8")


def reliability(mode: str) -> None:
    from agents.project2.policy import TrustedContext
    from api.project2_runtime_main import create_app
    from fastapi.testclient import TestClient

    protocol = ROOT / "evals/project2-v1/calibration_v031/protocol.json"
    samples = json.loads(protocol.read_text(encoding="utf-8"))["samples"]
    tasks = [
        {
            "sample_id": s["sample_id"],
            "group_sha256": s["query_sha256"],
            "body": {k: v for k, v in s.items() if k not in {"sample_id", "query_sha256"}},
        }
        for s in samples
    ]
    folder = AUDIT / mode
    if mode == "reliability_after":
        # Reproduce a cold namespace after the classification repair. Preserve
        # both the original cache and trial0 cache; no selective row deletion.
        cache = ROOT / ".rag_data/assignment_reliability_final_cache.sqlite"
        if cache.exists():
            raise ValueError("Registered cold cache already exists; do not silently reuse it")
        os.environ["PROJECT2_RERANK_CACHE"] = str(cache.resolve())
    lock(folder, tasks, mode)
    save(
        folder / "cache_registration.json",
        {
            "path": os.getenv("PROJECT2_RERANK_CACHE", ".rag_data/techqa_rerank_cache.sqlite"),
            "initial_new_namespace": "empty" if mode == "reliability_after" else "legacy retained",
            "reason": "cold namespace matches trial0; existing caches and failed trial preserved",
            "subject": "homework-evaluator",
            "tenant": "local",
            "resource_scope": "full",
        },
    )
    owner = TrustedContext(
        "homework-evaluator",
        "local",
        frozenset({"full"}),
        frozenset({"document_count", "compare_document_counts", "rag_explain"}),
    )
    rows = []
    app = create_app(credentials={"local-homework-eval": owner}, state_directory=folder / "state")
    with (
        HostGuard(folder / "power") as guard,
        TestClient(app) as client,
        (folder / "requests.jsonl").open("x", encoding="utf-8") as handle,
    ):
        for repeat in (1, 2, 3):
            order = list(tasks)
            random.Random(20261005 + repeat).shuffle(order)
            for index, task in enumerate(order, 1):
                guard.ensure_running()
                start = time.monotonic()
                result, error = {}, None
                try:
                    response = client.post(
                        "/v1/project2/analysis",
                        json=task["body"],
                        headers={"Authorization": "Bearer local-homework-eval"},
                    )
                    result = response.json()
                    if response.status_code != 200:
                        error = "http_" + str(response.status_code)
                except Exception as exc:
                    error = type(exc).__name__ + ": " + str(exc)[:400]
                states = {k: v["status"] for k, v in result.get("workers", {}).items()}
                usage = result.get("usage", {})
                row = {k: v for k, v in task.items() if k != "body"}
                row.update(
                    {
                        "repeat": repeat,
                        "result": result,
                        "error": error,
                        "elapsed_seconds": time.monotonic() - start,
                        "worker_failure": int(
                            bool(error)
                            or not states
                            or any(s in {"failed", "timeout"} for s in states.values())
                        ),
                        "complete": int(result.get("status") == "completed"),
                        "partial": int(result.get("status") == "partial"),
                        "attempts": usage.get("attempts"),
                        "llm_calls": usage.get("llm_calls"),
                        "observed_tokens": usage.get("observed_tokens"),
                        "cost": usage.get("cost"),
                        "evidence_type": "真实运行",
                    }
                )
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.flush()
                rows.append(row)
                LOGGER.info(
                    "%s repeat=%d %d/%d states=%s seconds=%.3f",
                    mode,
                    repeat,
                    index,
                    len(order),
                    states,
                    row["elapsed_seconds"],
                )
    summary(
        folder,
        rows,
        ["worker_failure", "complete", "partial", "elapsed_seconds", "attempts", "llm_calls"],
    )


def summary(folder: Path, rows: list[dict[str, Any]], keys: list[str]) -> None:
    save(
        folder / "summary.json",
        {
            "requests": len(rows),
            "independent_tasks": len({r["group_sha256"] for r in rows}),
            "repeats": 3,
            "partition": "tune",
            "heldout_new_calls": 0,
            "metrics": {
                k: metric(
                    rows,
                    k,
                    binary=k
                    in {
                        "worker_failure",
                        "complete",
                        "partial",
                        "n_refusal",
                        "citation_valid",
                        "target_cited",
                    },
                )
                for k in keys
            },
            "failures": [
                {k: r.get(k) for k in ("sample_id", "system", "repeat", "error")}
                for r in rows
                if r.get("error") or r.get("worker_failure")
            ],
            "plan_sha256": digest(folder / "plan.json"),
            "records_sha256": digest(folder / "requests.jsonl"),
            "superiority_claim": False,
            "cost": None,
            "cost_reason": "local models; monetary price and full token usage not observed",
            "s14_status": "未通过",
            "scope": "仅 tune/对照集，非 held-out 验证",
        },
    )


def chap11() -> None:
    import httpx
    from agents.project2.observability import observe_pipeline
    from agents.project2.rag_process import LocalDense
    from agents.rag_agent.factory import build_agent
    from models.schemas import QueryRequest
    from models.settings import Settings

    from evaluation_protocol.runner import body_f1, document_id
    from rag.api.runtime import build_service
    from rag.retrieval.filters import FilterPolicy
    from rag.techqa.embedding_server import SemanticSearch
    from rag.techqa.semantic import SEMANTIC_ROOT

    records = select_questions(ROOT, "tune")
    tasks = [
        {
            "sample_id": str(i),
            "group_sha256": hashlib.sha256(query(r["record"]).encode()).hexdigest(),
            "body": {"query": query(r["record"])},
            "query_form": (
                "context_or_rewrite"
                if re.search(r"\b(?:it|this|these|that|those)\b", query(r["record"]), re.I)
                or len(query(r["record"]).split()) < 8
                else "explicit"
            ),
        }
        for i, r in enumerate(records)
    ]
    folder = AUDIT / "chap11"
    lock(folder, tasks, "chap11-original-rag-vs-agentic")
    empty_case = next(
        task for task in tasks if re.search(r"\d+\.\d+|CVE-|\bIBM\b", task["body"]["query"], re.I)
    )
    empty_request = {**empty_case["body"], "filters": {"language": "zh-CN"}}
    save(
        folder / "empty_retrieval.plan.json",
        {
            "input": empty_request,
            "selection": "first registered query with technical literal",
            "purpose": (
                "Existing metadata filter no-result sample; "
                "not added to scored question set"
            ),
            "criteria": ["tool_called", "zero_candidates", "zero_sources", "zero_confidence"],
            "gold_oracle_used": False,
            "evidence_type": "故障注入",
        },
    )
    env = json.loads(
        (ROOT / "evals/protocol_v0/baseline_v0.config.json").read_text(encoding="utf-8")
    )["environment"]
    os.environ.update(env)
    os.environ["ANSWER_MODEL"] = env["AGENT_MODEL"]
    os.environ["OLLAMA_BASE_URL"] = env["AGENT_OLLAMA_URL"]
    engine = SemanticSearch(SEMANTIC_ROOT)
    simple, agent = build_service(), build_agent(Settings.from_env())
    # Identical real local dense service, avoiding a second 5GB index server;
    # no filtering, ranking, model, prompt or generator changes.
    simple.retriever.dense = LocalDense(engine, FilterPolicy())
    agent.retriever.pipeline.dense = LocalDense(engine, FilterPolicy())
    measurements = {"original_rag": {}, "agentic_rag": {}}
    observe_pipeline(simple.retriever, measurements["original_rag"])
    observe_pipeline(agent.retriever.pipeline, measurements["agentic_rag"])
    calls: dict[str, int] = {}
    tokens: dict[str, int] = {}
    original_send = httpx.AsyncClient.send

    async def observe_send(client: Any, request: Any, *args: Any, **kwargs: Any) -> Any:
        kind = (
            "llm"
            if request.url.path in {"/api/chat", "/api/generate"}
            else "embedding"
            if request.url.path == "/api/embed"
            else "http"
        )
        calls[kind] = calls.get(kind, 0) + 1
        response = await original_send(client, request, *args, **kwargs)
        if kind in {"llm", "embedding"} and not response.is_stream_consumed:
            # Do not consume an explicitly streamed response for observation.
            return response
        if kind in {"llm", "embedding"}:
            try:
                data = response.json()
            except ValueError:
                data = {}
            if not isinstance(data, dict):
                data = {}
            fields_observed = False
            for field in ("prompt_eval_count", "eval_count"):
                if isinstance(data.get(field), int):
                    tokens[field] = tokens.get(field, 0) + data[field]
                    fields_observed = True
            if fields_observed:
                tokens["responses_with_usage"] = tokens.get("responses_with_usage", 0) + 1
        return response

    httpx.AsyncClient.send = observe_send
    rows = []
    try:
        with (
            HostGuard(folder / "power") as guard,
            (folder / "requests.jsonl").open("x", encoding="utf-8") as handle,
        ):
            for repeat in (1, 2, 3):
                order = list(range(len(tasks)))
                random.Random(20261005 + repeat).shuffle(order)
                for index in order:
                    for system in ("original_rag", "agentic_rag"):
                        guard.ensure_running()
                        task = tasks[index]
                        calls.clear()
                        tokens.clear()
                        measurements[system].clear()
                        start, result, error = time.monotonic(), {}, None
                        try:
                            if system == "original_rag":
                                result = asyncio.run(
                                    simple.query(task["body"]["query"], mode="hybrid")
                                ).to_dict()
                            else:
                                result = asyncio.run(
                                    agent.run(
                                        QueryRequest.model_construct(**task["body"], filters={})
                                    )
                                ).model_dump(mode="json")
                        except Exception as exc:
                            error = type(exc).__name__ + ": " + str(exc)[:400]
                        elapsed = time.monotonic() - start
                        # Oracle begins here, strictly after retrieval/generation.
                        record = records[index]["record"]
                        response = (
                            result if system == "original_rag" else result.get("response", {})
                        )
                        answer = response.get("answer", "")
                        sources = response.get("citations", response.get("sources", []))
                        cited = set(re.findall(r"\[(S\d+)\]", answer))
                        valid = bool(cited) and cited <= {s.get("source_id") for s in sources}
                        trace = result.get("trace", {})
                        refused = (
                            response.get("refused", False)
                            if system == "original_rag"
                            else trace.get("status") == "unanswerable"
                        )
                        target = (
                            record.get("DOC_IDS", [None])[0]
                            if record.get("ANSWERABLE") == "Y"
                            else None
                        )
                        candidate_ids = measurements[system].get("candidate_ids", [])
                        ranks = [
                            i
                            for i, chunk_id in enumerate(candidate_ids, 1)
                            if target and document_id(chunk_id) == target
                        ]
                        rank = min(ranks) if ranks else None
                        row = {k: v for k, v in task.items() if k != "body"}
                        row.update(
                            {
                                "repeat": repeat,
                                "system": system,
                                "result": result,
                                "error": error,
                                "elapsed_seconds": elapsed,
                                "llm_calls": calls.get("llm", 0),
                                "embedding_calls": calls.get("embedding", 0),
                                "calls": sum(calls.values()),
                                "worker_failure": int(error is not None),
                                "citation_valid": int(valid) if not refused else None,
                                "n_refusal": int(bool(refused) and error is None)
                                if record.get("ANSWERABLE") == "N"
                                else None,
                                "target_cited": int(
                                    valid
                                    and any(
                                        document_id(s.get("chunk_id", "")) == target
                                        for s in sources
                                    )
                                )
                                if target
                                else None,
                                "body_f1": body_f1(answer, record["ANSWER"]) if target else None,
                                "observed_tokens": sum(
                                    tokens.get(key, 0)
                                    for key in ("prompt_eval_count", "eval_count")
                                )
                                if tokens
                                else None,
                                "provider_usage": dict(tokens),
                                "cost": None,
                                "evidence_type": "真实运行",
                                "question_type": "no_answer"
                                if record["ANSWERABLE"] == "N"
                                else task["query_form"],
                                "retrieval_observation": dict(measurements[system]),
                                "retrieval_recall5": int(rank is not None and rank <= 5)
                                if target
                                else None,
                                "retrieval_mrr": 1.0 / rank if rank else 0.0 if target else None,
                            }
                        )
                        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                        handle.flush()
                        rows.append(row)
                        LOGGER.info(
                            "chap11 %s repeat=%d sample=%s seconds=%.3f error=%s",
                            system,
                            repeat,
                            task["sample_id"],
                            elapsed,
                            error,
                        )
    finally:
        httpx.AsyncClient.send = original_send
    empty_run = asyncio.run(agent.run(QueryRequest.model_construct(**empty_request)))
    empty_value = empty_run.model_dump(mode="json")
    empty_trace, empty_response = empty_value["trace"], empty_value["response"]
    empty_checks = {
        "tool_called": empty_trace["tool_called"] is True,
        "zero_candidates": empty_trace["candidate_ids"] == [],
        "zero_sources": empty_response["sources"] == [],
        "zero_confidence": empty_response["confidence"] == 0,
    }
    save(
        folder / "empty_retrieval.result.json",
        {
            "result": empty_value,
            "checks": empty_checks,
            "status": "passed" if all(empty_checks.values()) else "failed",
            "diagnosis": (
                "Requested language filter excludes this official English corpus; "
                "failure stage is retrieval before context/answer selection. "
                "No unfiltered N-quality claim."
            ),
            "evidence_type": "故障注入",
            "scored_set_changed": False,
        },
    )
    summary(folder, rows, [])
    value = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    value["systems"] = {
        s: {
            k: metric(
                [r for r in rows if r["system"] == s],
                k,
                binary=k in {"worker_failure", "citation_valid", "n_refusal", "target_cited"},
            )
            for k in (
                "worker_failure",
                "citation_valid",
                "target_cited",
                "n_refusal",
                "body_f1",
                "elapsed_seconds",
                "llm_calls",
                "embedding_calls",
                "calls",
                "retrieval_recall5",
                "retrieval_mrr",
                "observed_tokens",
            )
        }
        for s in ("original_rag", "agentic_rag")
    }
    value["type_rule"] = (
        "Registered query-side form: pronoun it/this/these/that/those or fewer than "
        "8 whitespace words => context_or_rewrite; otherwise explicit. Official N "
        "is assigned only after response for scoring; it is not an online input."
    )
    value["retrieval_scope"] = (
        "Native returned bounded candidates before parent expansion; Recall@5 and "
        "MRR over that list. Original and Agentic retain their configured candidate limits."
    )
    value["token_scope"] = (
        "Observed Ollama prompt_eval_count + eval_count on completed non-streamed "
        "HTTP responses; unavailable or failed-response usage is not fabricated. "
        "No monetary price is assigned to local inference."
    )
    keys = (
        "body_f1",
        "citation_valid",
        "n_refusal",
        "retrieval_recall5",
        "retrieval_mrr",
        "elapsed_seconds",
        "llm_calls",
        "worker_failure",
    )
    value["by_type"] = {
        system: {
            kind: {
                key: metric(
                    [
                        row
                        for row in rows
                        if row["system"] == system and row["question_type"] == kind
                    ],
                    key,
                    binary=key
                    in {"citation_valid", "n_refusal", "retrieval_recall5", "worker_failure"},
                )
                for key in keys
            }
            for kind in ("explicit", "context_or_rewrite", "no_answer")
        }
        for system in ("original_rag", "agentic_rag")
    }
    comparisons = []
    for task in tasks:
        paired = {
            system: [
                row
                for row in rows
                if row["sample_id"] == task["sample_id"] and row["system"] == system
            ]
            for system in ("original_rag", "agentic_rag")
        }
        averages = {
            system: sum(float(row.get("body_f1") or 0) for row in selected) / len(selected)
            for system, selected in paired.items()
        }
        comparisons.append(
            {
                "sample_id": task["sample_id"],
                "query_form": task["query_form"],
                "means": averages,
                "delta": averages["agentic_rag"] - averages["original_rag"],
            }
        )
    value["answer_proxy_comparison"] = comparisons
    failures = [
        row
        for row in rows
        if row["system"] == "agentic_rag"
        and (
            row["error"]
            or row["result"].get("trace", {}).get("rewrite_fallback")
            or not row["result"].get("trace", {}).get("candidate_ids")
        )
    ]
    if failures:
        row = failures[0]
        trace = row["result"].get("trace", {})
        save(
            folder / "failure_diagnosis.json",
            {
                "sample_id": row["sample_id"],
                "repeat": row["repeat"],
                "error": row["error"],
                "stage": "rewrite" if trace.get("rewrite_fallback") else "retrieval",
                "original_query": trace.get("original_query"),
                "rewritten_query": trace.get("rewritten_query"),
                "rewrite_fallback": trace.get("rewrite_fallback"),
                "candidate_ids": trace.get("candidate_ids", []),
                "status": trace.get("status"),
                "evidence_type": "真实运行",
                "design_changed": False,
            },
        )
    save(folder / "summary.json", value)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["reliability_before", "reliability_after", "chap11"])
    args = parser.parse_args()
    chap11() if args.mode == "chap11" else reliability(args.mode)


if __name__ == "__main__":
    main()
