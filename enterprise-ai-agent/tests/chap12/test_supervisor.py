from __future__ import annotations

import asyncio
import itertools
from typing import Any

import pytest

from agents.chap12.budget import Budget, BudgetLimits
from agents.chap12.contracts import (
    AnalysisRequest,
    DbInput,
    DbPayload,
    RagInput,
    RagPayload,
    TrustedContext,
    WorkerResult,
)
from agents.chap12.db_worker import Catalog, Product
from agents.chap12.supervisor import Supervisor, merge
from tests.chap12.conftest import context

STATES = ["completed", "partial", "no_data", "permission_denied", "timeout", "failed"]
CATALOG = Catalog([Product("SSCRJU", "IBM Streams"), Product("SSFKSJ", "WebSphere MQ")])


def payload(worker: str, status: str = "completed") -> RagPayload | DbPayload:
    if worker == "rag":
        return RagPayload(answer="Set the variable with streamtool.", confidence=0.5,
                          rag_status="answered",
                          citations=[{"source_id": "S1", "doc_id": "swg21996508",
                                      "quote": "streamtool setproperty"}])
    return DbPayload(operation="count_documents", product_name="IBM Streams",
                     product_id="SSCRJU", date_from=None, date_to=None, doc_class=None,
                     metric="m", unit="documents", count=0 if status == "no_data" else 2,
                     snapshot="s",
                     query_template="count_documents")


class FakeWorker:
    def __init__(self, name: str, status: str = "completed", delay: float = 0.0,
                 error: Exception | None = None) -> None:
        self.name, self.status, self.delay, self.error = name, status, delay, error
        self.inputs: list[Any] = []

    async def run(self, run_id: str, task_id: str, request: Any, ctx: TrustedContext,
                  budget: Budget) -> WorkerResult:
        self.inputs.append(request)
        await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        useful = self.status in {"completed", "partial", "no_data"}
        return WorkerResult.model_validate({
            "run_id": run_id, "task_id": task_id, "worker": self.name, "status": self.status,
            "payload": payload(self.name, self.status) if useful else None,
            "error": None if useful else {"category": "internal", "message": self.status},
        })


def supervisor(rag: FakeWorker, db: FakeWorker, **limits: Any) -> Supervisor:
    return Supervisor({"rag": rag, "database": db}, CATALOG, BudgetLimits(**limits))


def go(sup: Supervisor, request: AnalysisRequest, ctx: TrustedContext | None = None):  # type: ignore[no-untyped-def]
    return asyncio.run(sup.run(request, ctx or context()))


def expected(rag: str, db: str) -> str:
    """Independent statement of the merge rule for two required tasks."""
    if rag == db == "completed":
        return "completed"
    if rag in {"completed", "partial"} or db in {"completed", "partial"}:
        return "partial"
    for state in ("permission_denied", "timeout", "failed", "no_data"):
        if state in (rag, db):
            return state
    raise AssertionError


@pytest.mark.parametrize(("rag", "db"), list(itertools.product(STATES, STATES)))
def test_all_36_worker_state_pairs(rag: str, db: str) -> None:
    result = go(supervisor(FakeWorker("rag", rag), FakeWorker("database", db)),
                AnalysisRequest(query="Streams 4.1.1.1 environment variables"))
    assert result.status == expected(rag, db) == merge([rag, db])
    assert [w.status for w in result.worker_results] == [rag, db]
    if result.status == "partial":
        assert result.limitations[0].startswith("部分完成")
    if rag not in {"completed", "partial"}:
        assert "streamtool" not in result.answer and result.citations == []
    if result.status not in {"completed", "partial", "no_data"}:
        # Only a complete zero count may still be shown; never an unfinished value.
        assert result.answer in {"未能给出有证据支持的结果。",
                                 "[数据] 样本快照中产品 IBM Streams（SSCRJU）的文档数：0。"}


@pytest.mark.parametrize(("goal", "called"), [
    ("explain", ["rag"]), ("data", ["database"]), ("explain_and_data", ["rag", "database"])])
def test_goal_routes_only_to_registered_tasks(goal: str, called: list[str]) -> None:
    rag, db = FakeWorker("rag"), FakeWorker("database")
    result = go(supervisor(rag, db), AnalysisRequest(query="IBM Streams jobs", goal=goal))  # type: ignore[arg-type]
    assert [t.worker for t in result.plan] == called
    assert bool(rag.inputs) == ("rag" in called) and bool(db.inputs) == ("database" in called)
    assert result.status == "completed"


def test_unknown_goal_and_fields_rejected() -> None:
    with pytest.raises(ValueError):
        AnalysisRequest.model_validate({"query": "x", "goal": "publish"})
    with pytest.raises(ValueError):
        AnalysisRequest.model_validate({"query": "x", "allowed_workers": ["database"]})


def test_unregistered_worker_is_never_called() -> None:
    rag = FakeWorker("rag")
    sup = Supervisor({"rag": rag}, CATALOG, BudgetLimits())
    result = go(sup, AnalysisRequest(query="IBM Streams"))
    assert [w.status for w in result.worker_results] == ["completed", "failed"]
    assert result.worker_results[1].error.message == "worker is not registered"  # type: ignore[union-attr]
    assert result.status == "partial"


def test_workers_receive_only_their_contract_input() -> None:
    rag, db = FakeWorker("rag"), FakeWorker("database")
    go(supervisor(rag, db), AnalysisRequest(query="Why do IBM Streams jobs fail?"))
    assert rag.inputs == [RagInput(query="Why do IBM Streams jobs fail?")]
    assert isinstance(db.inputs[0], DbInput) and db.inputs[0].product == "SSCRJU"
    assert set(RagInput.model_fields) == {"query"}


def test_explicit_data_request_overrides_slot_resolution() -> None:
    db = FakeWorker("database")
    go(supervisor(FakeWorker("rag"), db), AnalysisRequest.model_validate({
        "query": "IBM Streams", "goal": "data",
        "data_request": {"operation": "count_by_year", "product": "WebSphere MQ"}}))
    assert db.inputs[0].operation == "count_by_year" and db.inputs[0].product == "WebSphere MQ"


def test_unnamed_product_is_delegated_to_db_inference() -> None:
    db = FakeWorker("database")
    go(supervisor(FakeWorker("rag"), db), AnalysisRequest(query="ulimit settings"))
    assert db.inputs[0].product is None and db.inputs[0].infer_product
    assert db.inputs[0].query == "ulimit settings"


def test_global_permission_denial_calls_no_worker() -> None:
    rag, db = FakeWorker("rag"), FakeWorker("database")
    result = go(supervisor(rag, db), AnalysisRequest(query="IBM Streams"), context(workers=set()))
    assert result.status == "permission_denied"
    assert rag.inputs == db.inputs == [] and result.usage.tool_calls == 0


def test_request_deadline_cancels_slow_worker_and_keeps_fast_result() -> None:
    rag, db = FakeWorker("rag", delay=10), FakeWorker("database")
    result = go(supervisor(rag, db, deadline_seconds=0.3), AnalysisRequest(query="IBM Streams"))
    assert [w.status for w in result.worker_results] == ["timeout", "completed"]
    assert result.status == "partial" and result.usage.elapsed_ms < 3000
    assert result.data_result is not None and result.data_result.count == 2


def test_parallel_branches_do_not_serialize() -> None:
    rag, db = FakeWorker("rag", delay=0.4), FakeWorker("database", delay=0.4)
    result = go(supervisor(rag, db), AnalysisRequest(query="IBM Streams"))
    assert result.status == "completed" and result.usage.elapsed_ms < 750


def test_worker_crash_becomes_explicit_failure() -> None:
    result = go(supervisor(FakeWorker("rag", error=RuntimeError("boom")),
                           FakeWorker("database")), AnalysisRequest(query="IBM Streams"))
    assert result.worker_results[0].status == "failed" and result.status == "partial"
    assert result.worker_results[0].error.message == "RuntimeError"  # type: ignore[union-attr]


def test_final_response_carries_evidence_and_data_provenance() -> None:
    result = go(supervisor(FakeWorker("rag"), FakeWorker("database")),
                AnalysisRequest(query="IBM Streams"))
    assert result.citations[0].doc_id == "swg21996508"
    assert result.data_result.snapshot == "s" and "文档数：2" in result.answer  # type: ignore[union-attr]
    assert [e.event for e in result.trace][0] == "planned"
