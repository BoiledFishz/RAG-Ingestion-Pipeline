"""Program-owned six-state join, never delegated to an LLM."""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from uuid import uuid4

from agents.project2.budget import Budget, BudgetExceeded
from agents.project2.policy import TrustedContext
from models.project2 import AnalysisRequest, WorkerResult
from models.project2 import Status
from tools.techqa_document_query import DatabaseWorker, query_groups

LOGGER = logging.getLogger(__name__)


def source_lineage(trace: dict, cited: set[str]) -> list[dict]:
    candidates = trace.get("candidate_ids", [])
    ranks = {chunk: rank for rank, chunk in enumerate(candidates, 1)}
    return [{"source_id": item["source_id"], "chunk_id": item["chunk_id"],
             "source_file": item["source_file"], "page_number": item["page_number"],
             "candidate_rank": ranks.get(item["chunk_id"]),
             "candidate_stage": "parent_candidates_before_compression",
             "start_char": item.get("start_char"), "end_char": item.get("end_char"),
             "excerpt": item.get("excerpt", ""), "cited": item["source_id"] in cited}
            for item in trace.get("evidence", [])]


def combine_status(rag: Status, database: Status) -> Status:
    states = {"completed", "partial", "no_data", "permission_denied", "timeout", "failed"}
    if rag not in states or database not in states:
        raise ValueError("Unknown Worker status")
    pair = {rag, database}
    if rag == database == "completed":
        return "completed"
    if pair & {"completed", "partial"}:
        return "partial"
    if "permission_denied" in pair:
        return "permission_denied"
    if "failed" in pair:
        return "failed"
    if "timeout" in pair:
        return "timeout"
    return "no_data"


def empty_result(worker: str, status: Status, run_id: str, category: str) -> WorkerResult:
    return WorkerResult(run_id=run_id, task_id="rag_explain" if worker == "rag" else "techqa_document_query", worker=worker,
                        status=status, error={"category": category, "retryable": False})


def response(run_id: str, rag: WorkerResult, database: WorkerResult, budget: Budget) -> dict:
    overall = combine_status(rag.status, database.status)
    workers = {"rag": rag.model_dump(mode="json"), "database": database.model_dump(mode="json")}
    limitations = list(dict.fromkeys([*database.limitations, *rag.limitations]))
    if overall == "partial":
        covered = [name for name, worker in (("技术证据", rag), ("文档统计", database)) if worker.status in {"completed", "partial"}]
        missing = [f"{name}={worker.status}" for name, worker in (("技术证据", rag), ("文档统计", database)) if worker.status != "completed"]
        limitations.append("已覆盖：" + "、".join(covered) + "；缺口：" + "、".join(missing))
    return {"contract_version": "project2-v1", "run_id": run_id, "trace_id": run_id, "status": overall,
            "answer": rag.payload.get("answer", ""), "evidence": [*rag.evidence, *database.evidence],
            "data_results": database.payload, "worker_results": workers, "workers": workers,
            "usage": budget.snapshot(), "limitations": limitations}


class Supervisor:
    def __init__(self, database: DatabaseWorker, rag_process: object, *, registered_database_path: Path | None = None) -> None:
        self.database, self.rag_process = database, rag_process
        self.registered_database_path = registered_database_path.resolve() if registered_database_path else None

    async def run(self, request: AnalysisRequest, context: TrustedContext | None, budget: Budget) -> dict:
        run_id = uuid4().hex
        budget.run_id = run_id
        allowed_db = context is not None and context.permits(request.analysis_operation)
        allowed_rag = context is not None and context.permits("rag_explain")
        if not (allowed_db or allowed_rag):
            return response(run_id, empty_result("rag", "permission_denied", run_id, "permission_denied"),
                            empty_result("database", "permission_denied", run_id, "permission_denied"), budget)
        if allowed_db and self.registered_database_path is not None and self.database.path != self.registered_database_path:
            return response(run_id, empty_result("rag", "failed", run_id, "data_version_mismatch"),
                            empty_result("database", "failed", run_id, "data_version_mismatch"), budget)
        try:
            budget.remaining()
            if allowed_db:
                query_groups(request)
        except ValueError:
            return response(run_id, empty_result("rag", "failed", run_id, "clarification_required"),
                            empty_result("database", "failed", run_id, "clarification_required"), budget)
        database = await self.database.run(request, context, budget, run_id) if allowed_db else empty_result("database", "permission_denied", run_id, "permission_denied")
        budget.database_result = database
        if database.error and database.error["category"] == "data_version_mismatch":
            return response(run_id, empty_result("rag", "failed", run_id, "data_version_mismatch"), database, budget)
        rag = empty_result("rag", "permission_denied", run_id, "permission_denied")
        if allowed_rag:
            # Trusted server context, never a prompt/request-body grant.
            from agents.project2.cache_identity import authorization_scope
            assert context is not None
            budget.cache_scope = authorization_scope(context)
            try:
                message = await self.rag_process.run(request.query, budget)
                if message.get("budget_exceeded"):
                    rag = empty_result("rag", "timeout", run_id, message.get("budget_exceeded_reason") or "dependency_attempt_limit")
                elif message["type"] != "result":
                    rag = empty_result("rag", "failed", run_id, message.get("category", "rag_error"))
                else:
                    run = message["data"]
                    trace, answer = run["trace"], run["response"]
                    status = "completed" if trace["status"] == "answered" else "partial" if trace["status"] == "partial" else "failed" if trace["status"] == "invalid_evidence" else "no_data"
                    citations = set(re.findall(r"\[(S\d+)\]", answer["answer"]))
                    source_map = {source.get("source_id") for source in answer["sources"]}
                    if status in {"completed", "partial"} and (not answer["answer"].strip() or not answer["sources"] or not citations or not citations <= source_map):
                        rag = empty_result("rag", "failed", run_id, "invalid_evidence")
                        result = response(run_id, rag, database, budget)
                        LOGGER.warning("Project2 run=%s refused invalid external RAG evidence", run_id)
                        return result
                    rag = WorkerResult(run_id=run_id, task_id="rag_explain", worker="rag", status=status,
                                       payload={"answer": answer["answer"], "sources": answer["sources"], "confidence": answer["confidence"], "trace": trace,
                                                "original_query": trace.get("original_query", request.query),
                                                "actual_query": trace.get("rewritten_query", request.query),
                                                "pipeline": message.get("pipeline", {}),
                                                "source_lineage": source_lineage(trace, citations)},
                                       evidence=answer["sources"], usage=budget.snapshot(),
                                       limitations=["RAG状态由当前证据规则判断；confidence未校准，不是事实正确概率。"])
            except (BudgetExceeded, TimeoutError) as exc:
                LOGGER.warning("RAG run=%s timeout=%s", run_id, exc)
                rag = empty_result("rag", "timeout", run_id, "request_or_dependency_timeout")
            except Exception as exc:
                LOGGER.exception("RAG run=%s failed", run_id)
                rag = empty_result("rag", "failed", run_id, type(exc).__name__)
        result = response(run_id, rag, database, budget)
        LOGGER.info("Project2 run=%s status=%s attempts=%d", run_id, result["status"], budget.attempts)
        return result
