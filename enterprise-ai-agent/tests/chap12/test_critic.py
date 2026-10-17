"""Item 10: deterministic Critic and the single bounded Replan."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from agents.chap12.budget import Budget, BudgetLimits
from agents.chap12.contracts import (
    AnalysisRequest,
    DbInput,
    TrustedContext,
    WorkerResult,
)
from agents.chap12.critic import review
from agents.chap12.db_worker import DatabaseQueryWorker
from agents.chap12.supervisor import Supervisor
from tests.chap12.conftest import context

QUESTION = "Jobs do not inherit the environment variables after the upgrade"  # no product named


def rag_result(cited: list[str], status: str = "completed") -> WorkerResult:
    return WorkerResult.model_validate({
        "run_id": "r", "task_id": "T1-rag", "worker": "rag", "status": status,
        "payload": {"answer": "answer", "confidence": 0.9, "rag_status": "answered",
                    "retrieved_doc_ids": [*cited, "swg21903536"],
                    "citations": [{"source_id": f"S{i}", "doc_id": d, "quote": "quoted text"}
                                  for i, d in enumerate(cited, 1)]}})


def db_result(product: str | None, source: str = "inferred", status: str = "completed",
              clarification: bool = False) -> WorkerResult:
    if clarification:
        return WorkerResult.model_validate({
            "run_id": "r", "task_id": "T2-database", "worker": "database", "status": "no_data",
            "error": {"category": "clarification_required", "message": "specify"}})
    return WorkerResult.model_validate({
        "run_id": "r", "task_id": "T2-database", "worker": "database", "status": status,
        "payload": {"operation": "search_product_documents", "product_name": product,
                    "product_id": product, "product_source": source, "date_from": None,
                    "date_to": None, "doc_class": None, "metric": "m", "unit": "documents",
                    "snapshot": "s", "query_template": "search_product_documents",
                    "rows": [{"key": "swg1", "value": "x"}]}})


def products(mapping: dict[str, list[str]]) -> Any:
    return lambda docs: list(dict.fromkeys(p for d in docs for p in mapping.get(d, [])))


# ---- unit ----------------------------------------------------------------------------

def test_conflicting_inferred_product_triggers_replan() -> None:
    found = review(rag_result(["swg21996508"]), db_result("SSFKSJ"),
                   products({"swg21996508": ["SSCRJU"]}))
    assert found.replan_product == "SSCRJU" and found.findings[0].startswith("C2")


@pytest.mark.parametrize("source", ["explicit", "query_literal"])
def test_user_given_product_is_flagged_but_never_replaced(source: str) -> None:
    found = review(rag_result(["swg21996508"]), db_result("SSFKSJ", source),
                   products({"swg21996508": ["SSCRJU"]}))
    assert found.replan_product is None and found.findings[0].startswith("C2")


def test_unresolved_product_is_taken_from_citations() -> None:
    found = review(rag_result(["swg21996508"]), db_result(None, clarification=True),
                   products({"swg21996508": ["SSCRJU"]}))
    assert found.replan_product == "SSCRJU"


def test_consistent_or_uncited_results_need_nothing() -> None:
    mapping = products({"swg21996508": ["SSCRJU"]})
    assert review(rag_result(["swg21996508"]), db_result("SSCRJU"), mapping).findings == []
    refused = rag_result([], status="no_data")
    assert review(refused, db_result("SSFKSJ"), mapping).replan_product is None


def test_citation_outside_retrieved_set_is_reported() -> None:
    rag = rag_result(["swg21996508"])
    assert rag.payload is not None
    rag.payload.retrieved_doc_ids = ["swg00000000"]  # type: ignore[union-attr]
    found = review(rag, None, products({}))
    assert any("outside the retrieved" in f for f in found.findings)


# ---- integration with the real DB Worker ---------------------------------------------

class FakeRag:
    name = "rag"

    def __init__(self, cited: list[str]) -> None:
        self.cited = cited

    async def run(self, run_id: str, task_id: str, request: Any, ctx: TrustedContext,
                  budget: Budget) -> WorkerResult:
        budget.reserve("tool", self.name)
        result = rag_result(self.cited)
        return result.model_copy(update={"run_id": run_id, "task_id": task_id})


class CountingDb(DatabaseQueryWorker):
    calls: list[DbInput]

    async def run(self, run_id: str, task_id: str, request: DbInput, ctx: TrustedContext,
                  budget: Budget) -> WorkerResult:
        self.calls.append(request)
        return await super().run(run_id, task_id, request, ctx, budget)


@pytest.fixture
def wrong_inference(sample_index: Path, monkeypatch: pytest.MonkeyPatch) -> CountingDb:
    worker = CountingDb(sample_index)
    worker.calls = []

    async def wrong(query: str, ctx: TrustedContext) -> tuple[str, list[str], str]:
        return "SSFKSJ", [], "inferred"

    monkeypatch.setattr(worker, "_resolve", wrong)
    return worker


def supervise(db: DatabaseQueryWorker, ctx: TrustedContext | None = None,
              limits: BudgetLimits | None = None) -> Any:
    supervisor = Supervisor({"rag": FakeRag(["swg21996508"]), "database": db}, db.catalog,
                            limits)
    return asyncio.run(supervisor.run(AnalysisRequest(query=QUESTION), ctx or context()))


def test_replan_replaces_conflicting_data_once(wrong_inference: CountingDb) -> None:
    result = supervise(wrong_inference)
    assert len(wrong_inference.calls) == 2  # original + exactly one replan
    assert result.data_result.product_id == "SSCRJU"
    assert result.data_result.product_source == "rag_citation"
    assert [r.key for r in result.data_result.rows][0] == "swg21996508"
    assert any(e.event == "replan" for e in result.trace)
    assert any("Critic" in x for x in result.limitations)
    assert result.status == "completed"


def test_critic_off_keeps_original(wrong_inference: CountingDb,
                                   monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHAP12_CRITIC", "off")
    result = supervise(wrong_inference)
    assert len(wrong_inference.calls) == 1 and result.data_result.product_id == "SSFKSJ"


def test_replan_never_uses_unauthorized_product(wrong_inference: CountingDb) -> None:
    result = supervise(wrong_inference, context(products={"SSFKSJ"}))
    assert len(wrong_inference.calls) == 1
    assert result.data_result.product_id == "SSFKSJ"
    assert "SSCRJU" not in str(result.model_dump())


def test_replan_respects_budget(wrong_inference: CountingDb) -> None:
    # 3 tool calls: rag, db, and nothing left for the replan's DB tool reservation.
    result = supervise(wrong_inference, limits=BudgetLimits(max_tool_calls=2))
    assert result.data_result.product_id == "SSFKSJ"  # original kept
    assert any("复核后重新查询未成功" in x for x in result.limitations)
    assert result.usage.tool_calls <= 2
