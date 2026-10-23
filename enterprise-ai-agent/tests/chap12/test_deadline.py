"""P0-3: deadlines stop real synchronous work, not only coroutines.

Work runs in threads (asyncio.to_thread). Cancelling the awaiting coroutine cannot stop a
thread, so every external/expensive call re-checks the request deadline before starting
(budget.charge). These tests use genuinely blocking time.sleep inside the thread."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

import pytest

from agents.chap12 import supervisor as supervisor_module
from agents.chap12.budget import Budget, BudgetExhausted, BudgetLimits, metered
from agents.chap12.contracts import AnalysisRequest, RagInput
from agents.chap12.db_worker import DatabaseQueryWorker
from agents.chap12.supervisor import Supervisor
from tests.chap12.conftest import context
from tests.chap12.test_supervisor import FakeWorker

UNNAMED = "Jobs do not pick up environment variables from .bashrc with ODBC operators"


def capture_budget(monkeypatch: pytest.MonkeyPatch) -> list[Budget]:
    created: list[Budget] = []

    class Recording(Budget):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            created.append(self)

    monkeypatch.setattr(supervisor_module, "Budget", Recording)
    return created


def test_blocked_db_thread_starts_no_sql_after_deadline(sample_index: Path,
                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    budgets = capture_budget(monkeypatch)
    worker = DatabaseQueryWorker(sample_index)
    original = worker.index.search
    outcome: dict[str, Any] = {}

    def slow_search(query: str, limit: int = 30) -> Any:
        time.sleep(0.8)  # real blocking work in the worker thread
        try:
            return original(query, limit)
        except BudgetExhausted as exc:
            outcome["blocked"] = exc.kind
            raise

    monkeypatch.setattr(worker.index, "search", slow_search)
    sup = Supervisor({"rag": FakeWorker("rag"), "database": worker}, worker.catalog,
                     BudgetLimits(deadline_seconds=0.3))
    result = asyncio.run(sup.run(AnalysisRequest(query=UNNAMED, goal="data"), context()))
    assert result.status == "timeout" and result.worker_results[0].status == "timeout"
    used_at_return = dict(budgets[0].used)
    time.sleep(1.2)  # let the abandoned thread wake up and try to continue
    assert outcome.get("blocked") == "deadline"
    assert budgets[0].used == used_at_return and used_at_return["sql"] == 0


def test_blocked_encoder_thread_cannot_trigger_further_calls(sample_index: Path,
                                                            monkeypatch: pytest.MonkeyPatch
                                                            ) -> None:
    from agents.chap12.rag_worker import RagWorker
    from agents.rag_agent.compression import ContextCompressor
    from agents.rag_agent.generation import ExtractiveSelector
    from agents.rag_agent.rewrite import RuleRewriter
    from agents.rag_agent.service import RAGAgent
    from tools.sample_retriever import SampleRetrieverTool

    class SlowRetriever(SampleRetrieverTool):
        async def invoke(self, request: Any) -> Any:
            await asyncio.to_thread(time.sleep, 0.8)  # blocking work in a thread
            return await super().invoke(request)

    monkeypatch.setenv("TECHQA_PROFILE", "fixture")
    agent = RAGAgent(rewriter=RuleRewriter(), selector=ExtractiveSelector(),
                     retriever=SlowRetriever(sample_index, rerank="lexical", use_dense=False),
                     compressor=ContextCompressor(2400, 8, 0.2), top_k=8)
    budget = Budget(BudgetLimits(deadline_seconds=0.3))
    worker = RagWorker(agent, timeout=10)
    result = asyncio.run(worker.run("r", "t", RagInput(
        query="Streams jobs do not inherit environment variables"), context(), budget))
    assert result.status == "timeout"
    used_at_return = dict(budget.used)
    time.sleep(1.2)
    assert budget.used == used_at_return and used_at_return["sql"] == 0


def test_charge_after_deadline_raises_in_thread() -> None:
    budget = Budget(BudgetLimits(deadline_seconds=0.05))
    time.sleep(0.1)

    def call() -> None:
        from agents.chap12.budget import charge

        charge("sql")

    async def main() -> None:
        with metered(budget, "database"):
            await asyncio.to_thread(call)

    with pytest.raises(BudgetExhausted) as info:
        asyncio.run(main())
    assert info.value.kind == "deadline" and budget.used["sql"] == 0
