"""Central Supervisor: validate, authorize, plan, dispatch, merge, render.

State ownership (written by -> read by):
  run_id, plan, inputs ............ Supervisor -> Workers (each only its own input)
  results[worker] ................. that Worker's return value -> Supervisor (merge)
  budget counters ................. Budget (reserve) -> Workers/Supervisor (usage)
  status, answer, limitations ..... Supervisor only
RAG and DB have no data dependency, so they run concurrently; each writes only its own
result object and the Supervisor merges after both finish or the deadline cancels them.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Protocol

from agents.chap12 import planner
from agents.chap12.budget import Budget, BudgetLimits
from agents.chap12.contracts import (
    USEFUL,
    AnalysisRequest,
    DbPayload,
    FinalResponse,
    RagPayload,
    TaskSpec,
    TraceEvent,
    TrustedContext,
    Usage,
    WorkerError,
    WorkerResult,
)
from agents.chap12.db_worker import Catalog

PRIORITY = ("permission_denied", "timeout", "failed", "no_data")


class Worker(Protocol):
    name: str

    async def run(self, run_id: str, task_id: str, request: Any, ctx: TrustedContext,
                  budget: Budget) -> WorkerResult: ...


def merge(statuses: list[str]) -> str:
    """Overall status for required tasks. Never upgrades a failure to success."""
    if not statuses:
        return "failed"
    if all(s == "completed" for s in statuses):
        return "completed"
    if any(s in USEFUL for s in statuses):
        return "partial"
    for status in PRIORITY:
        if status in statuses:
            return status
    return "failed"


class Supervisor:
    def __init__(self, workers: dict[str, Worker], catalog: Catalog,
                 limits: BudgetLimits | None = None) -> None:
        self.workers, self.catalog = workers, catalog
        self.limits = limits or BudgetLimits()

    async def run(self, request: AnalysisRequest, ctx: TrustedContext) -> FinalResponse:
        run_id = uuid.uuid4().hex
        budget = Budget(self.limits)
        trace: list[TraceEvent] = []

        def event(node: str, name: str, detail: str = "") -> None:
            trace.append(TraceEvent(at_ms=round(budget.elapsed_ms(), 2), node=node, event=name,
                                    detail=detail))

        tasks = planner.plan(request)
        event("supervisor", "planned", ",".join(t.worker for t in tasks))
        notes: list[str] = []
        inputs: dict[str, Any] = {}
        for task in tasks:
            if task.worker == "rag":
                inputs[task.task_id] = planner.rag_input(request)
            else:
                inputs[task.task_id], extra = planner.db_input(request, self.catalog)
                notes += extra

        results: dict[str, WorkerResult] = {}
        if not any(t.worker in ctx.allowed_workers for t in tasks):
            # Global denial: no Worker is invoked and nothing is retrieved or counted.
            for task in tasks:
                results[task.task_id] = self._synthetic(run_id, task, "permission_denied",
                                                        "permission_denied",
                                                        "subject is not authorized")
            event("supervisor", "denied", "no authorized worker; zero calls")
        else:
            runnable: dict[str, asyncio.Task[WorkerResult]] = {}
            for task in tasks:
                worker = self.workers.get(task.worker)
                if worker is None:
                    results[task.task_id] = self._synthetic(run_id, task, "failed", "internal",
                                                            "worker is not registered")
                    continue
                event(task.worker, "dispatched", task.task_id)
                runnable[task.task_id] = asyncio.create_task(
                    worker.run(run_id, task.task_id, inputs[task.task_id], ctx, budget))
            if runnable:
                done, pending = await asyncio.wait(runnable.values(),
                                                   timeout=budget.remaining() + 0.5)
                for task_handle in pending:
                    task_handle.cancel()
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)
                specs = {t.task_id: t for t in tasks}
                for task_id, handle in runnable.items():
                    spec = specs[task_id]
                    if handle in pending:
                        results[task_id] = self._synthetic(run_id, spec, "timeout", "timeout",
                                                           "cancelled at request deadline")
                    elif handle.exception() is not None:
                        results[task_id] = self._synthetic(
                            run_id, spec, "failed", "internal",
                            type(handle.exception()).__name__)
                    else:
                        results[task_id] = handle.result()
                    event(spec.worker, "result", results[task_id].status)

        ordered = [results[t.task_id] for t in tasks]
        status = merge([r.status for r in ordered])
        event("supervisor", "merged", status)
        return self._render(run_id, request, tasks, ordered, status, notes, budget, trace)

    @staticmethod
    def _synthetic(run_id: str, task: TaskSpec, status: str, category: str,
                   message: str) -> WorkerResult:
        return WorkerResult.model_validate({
            "run_id": run_id, "task_id": task.task_id, "worker": task.worker, "status": status,
            "error": WorkerError.model_validate({"category": category, "message": message}),
        })

    @staticmethod
    def _render(run_id: str, request: AnalysisRequest, tasks: list[TaskSpec],
                results: list[WorkerResult], status: str, notes: list[str], budget: Budget,
                trace: list[TraceEvent]) -> FinalResponse:
        parts: list[str] = []
        citations = []
        data: DbPayload | None = None
        limitations = list(notes)
        for result in results:
            payload = result.payload
            if isinstance(payload, RagPayload) and result.status in USEFUL:
                parts.append(payload.answer)
                citations = payload.citations
            elif isinstance(payload, DbPayload) and result.status in USEFUL | {"no_data"}:
                data = payload
                parts.append(_data_sentence(payload))
            if result.status not in USEFUL:
                reason = result.error.message if result.error else "no publishable result"
                label = "技术解释" if result.worker == "rag" else "数据查询"
                limitations.append(f"{label}未完成（{result.status}）：{reason}")
            limitations += [x for x in result.limitations if x not in limitations]
        if not parts:
            parts.append("未能给出有证据支持的结果。")
        if status == "partial":
            limitations.insert(0, "部分完成：仅包含已完成部分，不能视为完整回答。")
        usage = Usage(
            llm_calls=budget.used["llm"], embedding_calls=budget.used["embedding"],
            db_queries=budget.used["db"], tool_calls=budget.used["tool"],
            sql_statements=budget.used["sql"], local_compute=budget.used["local"],
            embedding_cache_hits=budget.embedding_cache_hits,
            prompt_tokens=budget.prompt_tokens, completion_tokens=budget.completion_tokens,
            tokens=None if budget.prompt_tokens is None and budget.completion_tokens is None
            else (budget.prompt_tokens or 0) + (budget.completion_tokens or 0),
            retries=sum(r.usage.retries for r in results), elapsed_ms=budget.elapsed_ms(),
        )
        return FinalResponse(run_id=run_id, status=status, goal=request.goal,  # type: ignore[arg-type]
                             plan=tasks, answer="\n\n".join(parts), citations=citations,
                             data_result=data, limitations=limitations, worker_results=results,
                             usage=usage, trace=trace)


def _data_sentence(payload: DbPayload) -> str:
    scope = []
    if payload.date_from or payload.date_to:
        scope.append(f"{payload.date_from or '最早'} 至 {payload.date_to or '最新'}")
    if payload.doc_class:
        scope.append(f"类别 {payload.doc_class}")
    condition = f"（{'，'.join(scope)}）" if scope else ""
    if payload.operation == "count_documents":
        return (f"[数据] 样本快照中产品 {payload.product_name}（{payload.product_id}）"
                f"{condition}的文档数：{payload.count}。")
    if payload.operation == "list_recent_documents":
        lines = "\n".join(f"- {r.key}（{r.value}）" for r in payload.rows) or "- 无"
        more = "\n（同产品还有更多文档，仅列出最近几篇）" if payload.truncated else ""
        return (f"[相关文档] 样本知识库中产品 {payload.product_name}{condition}最近的文档："
                f"\n{lines}{more}")
    rows = "；".join(f"{r.key}: {r.value}" for r in payload.rows)
    more = "（结果已截断）" if payload.truncated else ""
    return f"[数据] {payload.product_name}{condition}按年份文档数：{rows or '无'}{more}。"

