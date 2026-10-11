from __future__ import annotations

import asyncio
from typing import Any

import pytest

from agents.chap12.budget import Budget, BudgetedModel, BudgetLimits
from agents.chap12.contracts import RagInput
from agents.chap12.rag_worker import RagWorker
from models.errors import DependencyUnavailable
from models.schemas import AgentResponse, AgentRun, QueryRequest, RunTrace, Source
from tests.chap12.conftest import context

SOURCE = Source(source_id="S1", chunk_id="techqa:swg21996508:parent",
                source_file="techqa://swg21996508", page_number=1,
                quote="streamtool setproperty --application-ev")


class FakeAgent:
    def __init__(self, status: str = "answered", sources: bool = True, delay: float = 0,
                 error: Exception | None = None, model: Any = None, llm_calls: int = 0) -> None:
        self.status, self.sources, self.delay, self.error = status, sources, delay, error
        self.model, self.llm_calls, self.calls = model, llm_calls, 0

    async def run(self, request: QueryRequest) -> AgentRun:
        self.calls += 1
        for _ in range(self.llm_calls):
            await self.model.generate("p", {})
        await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        sources = [SOURCE] if self.sources else []
        return AgentRun(
            response=AgentResponse(answer="Set it with streamtool." if sources else "无法回答",
                                   sources=sources, confidence=0.6 if sources else 0),
            trace=RunTrace(original_query=request.query, status=self.status,  # type: ignore[arg-type]
                           candidate_ids=["techqa:swg21996508:parent",
                                          "techqa:swg1PK69015:parent"]))


def run(agent: FakeAgent, limits: BudgetLimits | None = None, ctx=None, timeout: float = 5):  # type: ignore[no-untyped-def]
    budget = Budget(limits or BudgetLimits())
    worker = RagWorker(agent, timeout=timeout)
    return asyncio.run(worker.run("r", "t", RagInput(query="q"), ctx or context(), budget)), budget


def test_completed_answer_keeps_citations_and_retrieval_trace() -> None:
    result, budget = run(FakeAgent())
    assert result.status == "completed" and budget.used["tool"] == 1
    assert result.payload.citations[0].doc_id == "swg21996508"  # type: ignore[union-attr]
    assert result.payload.retrieved_doc_ids == ["swg21996508", "swg1PK69015"]  # type: ignore[union-attr]


@pytest.mark.parametrize(("status", "expected"), [
    ("partial", "partial"), ("unanswerable", "no_data"), ("clarified", "no_data"),
    ("invalid_evidence", "failed")])
def test_status_mapping(status: str, expected: str) -> None:
    result, _ = run(FakeAgent(status, sources=status == "partial"))
    assert result.status == expected


def test_answer_without_evidence_is_not_success() -> None:
    result, _ = run(FakeAgent("answered", sources=False))
    assert result.status == "no_data"


def test_timeout_and_dependency_failure_are_explicit() -> None:
    slow, _ = run(FakeAgent(delay=5), timeout=0.2)
    assert slow.status == "timeout" and slow.error.retryable  # type: ignore[union-attr]
    down, _ = run(FakeAgent(error=DependencyUnavailable("ollama down")))
    assert down.status == "failed" and down.error.category == "dependency_unavailable"  # type: ignore[union-attr]


def test_llm_budget_stops_the_call_before_it_starts() -> None:
    calls: list[str] = []

    class Model:
        async def generate(self, prompt: str, schema: dict[str, Any]) -> str:
            calls.append(prompt)
            return "{}"

    result, budget = run(FakeAgent(model=BudgetedModel(Model()), llm_calls=3),
                         BudgetLimits(max_llm_calls=2))
    assert result.status == "failed" and result.error.category == "budget_exhausted"  # type: ignore[union-attr]
    assert len(calls) == 2 and budget.used["llm"] == 2 and result.usage.llm_calls == 2


def test_permission_denied_does_not_call_agent() -> None:
    agent = FakeAgent()
    result, _ = run(agent, ctx=context(workers={"database"}))
    assert result.status == "permission_denied" and agent.calls == 0
