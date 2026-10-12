"""RAG Worker: the Project 1 RAGAgent behind the Chap12 Worker contract."""

from __future__ import annotations

import asyncio
import time
from typing import Protocol

from agents.chap12.budget import Budget, BudgetExhausted, metered
from agents.chap12.contracts import (
    Citation,
    RagInput,
    RagPayload,
    TrustedContext,
    WorkerError,
    WorkerResult,
)
from agents.chap12.scope import product_scope
from models.errors import DependencyUnavailable
from models.schemas import AgentRun, QueryRequest

LIMITATIONS = [
    "检索范围仅为本次样本快照（随机 TechQA 训练题的官方候选文档并集），不是全量知识库。",
    "confidence 是证据覆盖启发值，不是校准过的正确概率；引用存在不代表答案事实正确。",
]
SCOPE_LIMITATION = "检索只覆盖调用方被授权的产品文档；其他产品的文档未被检索。"
STATUS = {"answered": "completed", "partial": "partial", "unanswerable": "no_data",
          "clarified": "no_data", "invalid_evidence": "failed"}


class Agent(Protocol):
    async def run(self, request: QueryRequest) -> AgentRun: ...


def doc_id(reference: str) -> str:
    """techqa://ID or techqa:ID:parent -> ID."""
    if reference.startswith("techqa://"):
        return reference.removeprefix("techqa://")
    parts = reference.split(":")
    return parts[1] if len(parts) >= 2 and parts[0] == "techqa" else reference


class RagWorker:
    name = "rag"

    def __init__(self, agent: Agent, *, timeout: float = 140.0) -> None:
        self.agent, self.timeout = agent, timeout

    async def run(self, run_id: str, task_id: str, request: RagInput, ctx: TrustedContext,
                  budget: Budget) -> WorkerResult:
        started = time.monotonic()
        limitations = list(LIMITATIONS)
        if "*" not in ctx.allowed_product_ids:
            limitations.append(SCOPE_LIMITATION)

        def result(status: str, payload: RagPayload | None = None,
                   error: WorkerError | None = None) -> WorkerResult:
            return WorkerResult.model_validate({
                "run_id": run_id, "task_id": task_id, "worker": self.name, "status": status,
                "payload": payload, "error": error, "limitations": limitations,
                "usage": {
                    "llm_calls": budget.worker_count(self.name, "llm"),
                    "embedding_calls": budget.worker_count(self.name, "embedding"),
                    "sql_statements": budget.worker_count(self.name, "sql"),
                    "local_compute": budget.worker_count(self.name, "local"),
                    "tool_calls": budget.worker_count(self.name, "tool"),
                    "elapsed_ms": (time.monotonic() - started) * 1000,
                },
            })

        def error(status: str, category: str, message: str, retryable: bool = False
                  ) -> WorkerResult:
            return result(status, error=WorkerError.model_validate(
                {"category": category, "message": message, "retryable": retryable}))

        if self.name not in ctx.allowed_workers:
            return error("permission_denied", "permission_denied", "RAG is not authorized")
        try:
            budget.reserve("tool", self.name)
            with metered(budget, self.name), product_scope(ctx.allowed_product_ids):
                run = await asyncio.wait_for(self.agent.run(QueryRequest(query=request.query)),
                                             timeout=min(self.timeout, budget.remaining()))
        except TimeoutError:
            return error("timeout", "timeout", "RAG exceeded its deadline", retryable=True)
        except BudgetExhausted as exc:
            return error("failed", "budget_exhausted", str(exc))
        except DependencyUnavailable as exc:
            return error("failed", "dependency_unavailable", str(exc), retryable=True)
        except ValueError as exc:
            return error("failed", "invalid_input", str(exc)[:300])

        trace, response = run.trace, run.response
        status = STATUS.get(trace.status, "failed")
        titles = {e.source_id: e.title for e in trace.evidence}
        payload = RagPayload(
            answer=response.answer,
            citations=[Citation(source_id=s.source_id, doc_id=doc_id(s.source_file),
                                title=titles.get(s.source_id, ""), quote=s.quote)
                       for s in response.sources],
            confidence=response.confidence, rag_status=trace.status,
            rewritten_query=trace.rewritten_query,
            retrieved_doc_ids=list(dict.fromkeys(doc_id(c) for c in trace.candidate_ids)),
        )
        if status == "failed":
            return result(status, payload, WorkerError(
                category="invalid_evidence", message="evidence validation failed after retry"))
        if status in {"completed", "partial"} and not payload.citations:
            # A published answer must carry evidence; otherwise it is not a success.
            return result("no_data", payload)
        return result(status, payload)
