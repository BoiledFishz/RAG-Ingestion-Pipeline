from __future__ import annotations

import asyncio
import sqlite3
import time
from datetime import date
from pathlib import Path

import pytest

from agents.chap12.budget import Budget, BudgetLimits
from agents.chap12.contracts import DbInput
from agents.chap12.db_worker import DatabaseQueryWorker
from tests.chap12.conftest import context, fixture_docs


def independent_count(product_id: str, start: str | None = None, end: str | None = None) -> int:
    """Recount from the original JSON, sharing no code with the Worker."""
    total = 0
    for doc in fixture_docs():
        meta = doc["metadata"]
        assert isinstance(meta, dict)
        ids = {p.strip() for p in str(meta.get("productId") or "").split(",")}
        day = str(meta.get("date") or "")
        if product_id in ids and (not start or day >= start) and (not end or day <= end):
            total += 1
    return total


def run(worker: DatabaseQueryWorker, request: DbInput, ctx=None, limits=None):  # type: ignore[no-untyped-def]
    budget = Budget(limits or BudgetLimits())
    return asyncio.run(worker.run("r", "t", request, ctx or context(), budget)), budget


@pytest.fixture
def worker(sample_index: Path) -> DatabaseQueryWorker:
    return DatabaseQueryWorker(sample_index)


@pytest.mark.parametrize("product", ["SSFKSJ", "SSEQTP", "SSSHTQ", "SSCRJU"])
def test_count_matches_independent_recount(worker, product) -> None:  # type: ignore[no-untyped-def]
    result, budget = run(worker, DbInput(operation="count_documents", product=product))
    assert result.status == "completed"
    assert result.payload.count == independent_count(product)  # type: ignore[union-attr]
    assert result.payload.unit == "documents" and budget.used["db"] == 1  # type: ignore[union-attr]
    assert any("不是 IBM 全量知识库" in x for x in result.limitations)


def test_multi_product_documents_counted_once_per_product(worker) -> None:  # type: ignore[no-untyped-def]
    # One fixture document is tagged SSEQTP,SS7K4U,SSFKSJ,...: it counts for each tag.
    result, _ = run(worker, DbInput(operation="count_documents", product="WebSphere MQ"))
    assert result.payload.count == independent_count("SSFKSJ") == 4  # type: ignore[union-attr]


def test_date_range_and_year_breakdown(worker) -> None:  # type: ignore[no-untyped-def]
    ranged, _ = run(worker, DbInput(operation="count_documents", product="SSSHTQ",
                                    date_from=date(2018, 1, 1), date_to=date(2018, 12, 31)))
    assert ranged.payload.count == independent_count("SSSHTQ", "2018-01-01", "2018-12-31") == 1  # type: ignore[union-attr]
    yearly, _ = run(worker, DbInput(operation="count_by_year", product="SSSHTQ"))
    assert [(r.key, r.value) for r in yearly.payload.rows] == [("2017", 1), ("2018", 1)]  # type: ignore[union-attr]
    assert yearly.payload.count == independent_count("SSSHTQ")  # type: ignore[union-attr]


def test_result_size_limit_marks_truncation(worker) -> None:  # type: ignore[no-untyped-def]
    result, _ = run(worker, DbInput(operation="list_recent_documents", product="SSCRJU", limit=1))
    assert result.status == "completed"
    assert len(result.payload.rows) == 1 and result.payload.truncated  # type: ignore[union-attr]
    assert result.payload.rows[0].key == "swg21996508"  # newest first  # type: ignore[union-attr]
    with pytest.raises(ValueError):
        DbInput(operation="list_recent_documents", product="SSCRJU", limit=11)


def test_true_zero_is_no_data_with_count(worker) -> None:  # type: ignore[no-untyped-def]
    result, _ = run(worker, DbInput(operation="count_documents", product="SSSHTQ",
                                    date_from=date(1990, 1, 1), date_to=date(1990, 12, 31)))
    assert result.status == "no_data" and result.payload.count == 0  # type: ignore[union-attr]


@pytest.mark.parametrize("product", ["WebSphere MQ' OR 1=1 --", "technotes", "SELECT * FROM docs"])
def test_unknown_or_injected_product_rejected_before_sql(worker, product) -> None:  # type: ignore[no-untyped-def]
    result, budget = run(worker, DbInput(operation="count_documents", product=product))
    assert result.status == "failed" and result.error.category == "invalid_input"  # type: ignore[union-attr]
    assert budget.used["db"] == 0


def test_unregistered_operation_is_rejected_by_contract() -> None:
    with pytest.raises(ValueError):
        DbInput.model_validate({"operation": "drop_table", "product": "SSFKSJ"})
    with pytest.raises(ValueError):
        DbInput.model_validate({"operation": "count_documents", "product": "SSFKSJ",
                                "sql": "SELECT 1"})


def test_out_of_scope_product_and_operation_denied_without_query(worker) -> None:  # type: ignore[no-untyped-def]
    scoped = context(products={"SSCRJU"})
    result, budget = run(worker, DbInput(operation="count_documents", product="SSFKSJ"), scoped)
    assert result.status == "permission_denied" and budget.used["db"] == 0
    allowed, _ = run(worker, DbInput(operation="count_documents", product="SSCRJU"), scoped)
    assert allowed.status == "completed"
    denied, budget = run(worker, DbInput(operation="count_by_year", product="SSCRJU"),
                         context(ops={"count_documents"}))
    assert denied.status == "permission_denied" and budget.used["db"] == 0


def test_missing_product_needs_clarification_not_failure(worker) -> None:  # type: ignore[no-untyped-def]
    result, budget = run(worker, DbInput(operation="count_documents"))
    assert result.status == "no_data" and result.error.category == "clarification_required"  # type: ignore[union-attr]
    assert budget.used["db"] == 0


def test_product_inferred_from_own_bm25_when_not_named(worker) -> None:  # type: ignore[no-untyped-def]
    query = "Jobs do not pick up environment variables from .bashrc with ODBC operators"
    assert worker.catalog.find(query) == []  # no product named literally
    result, budget = run(worker, DbInput(operation="count_documents", infer_product=True,
                                         query=query, product_source="query_literal"))
    assert result.status == "completed" and budget.used["db"] == 2
    assert result.payload.product_id == "SSCRJU"  # type: ignore[union-attr]
    assert result.payload.product_source == "inferred"  # type: ignore[union-attr]
    assert len(result.payload.inference_doc_ids) == 3  # type: ignore[union-attr]
    assert result.limitations[0].startswith("问题未写明目录中的产品名")


def test_inference_without_agreement_asks_for_clarification(worker) -> None:  # type: ignore[no-untyped-def]
    result, _ = run(worker, DbInput(operation="count_documents", infer_product=True,
                                    query="zzqx unknownterm"))
    assert result.status == "no_data" and result.error.category == "clarification_required"  # type: ignore[union-attr]


def test_inferred_product_still_obeys_scope(worker) -> None:  # type: ignore[no-untyped-def]
    query = "Jobs do not pick up environment variables from .bashrc with ODBC operators"
    result, _ = run(worker, DbInput(operation="count_documents", infer_product=True, query=query),
                    context(products={"SSFKSJ"}))
    assert result.status == "permission_denied" and result.payload is None


def test_db_budget_enforced_before_execution(worker) -> None:  # type: ignore[no-untyped-def]
    result, budget = run(worker, DbInput(operation="count_documents", product="SSFKSJ"),
                         limits=BudgetLimits(max_db_queries=0))
    assert result.error.category == "budget_exhausted" and budget.used["db"] == 0  # type: ignore[union-attr]


def test_statement_deadline_interrupts_and_maps_to_timeout(worker, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    with worker.connect(time.monotonic() - 1) as db, pytest.raises(sqlite3.OperationalError,
                                                                   match="interrupt"):
        db.execute("WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c "
                   "LIMIT 50000000) SELECT count(*) FROM c").fetchall()

    def interrupted(*args: object) -> None:
        raise sqlite3.OperationalError("interrupted")

    monkeypatch.setattr(worker, "_execute", interrupted)
    result, _ = run(worker, DbInput(operation="count_documents", product="SSFKSJ"))
    assert result.status == "timeout" and result.payload is None


def test_connection_is_read_only(worker) -> None:  # type: ignore[no-untyped-def]
    with worker.connect(time.monotonic() + 5) as db, pytest.raises(sqlite3.OperationalError):
        db.execute("DELETE FROM technotes")


def test_transient_error_retry_is_bounded(worker, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[int] = []

    def locked(*args: object) -> list[tuple[int]]:
        calls.append(1)
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(worker, "_execute", locked)
    result, budget = run(worker, DbInput(operation="count_documents", product="SSFKSJ"))
    assert result.status == "failed" and result.usage.retries == 1
    assert len(calls) == 2 and budget.used["db"] == 2 and result.error.retryable  # type: ignore[union-attr]

    def once(*args: object) -> list[tuple[int]]:
        calls.append(1)
        if len(calls) == 3:
            raise sqlite3.OperationalError("database is locked")
        return [(7,)]

    monkeypatch.setattr(worker, "_execute", once)
    result, _ = run(worker, DbInput(operation="count_documents", product="SSFKSJ"))
    assert result.status == "completed" and result.usage.retries == 1


def test_catalog_resolution(worker) -> None:  # type: ignore[no-untyped-def]
    find = worker.catalog.find
    assert [p.product_id for p in find("SSL mutual auth in IBM HTTP Server v7")] == ["SSEQTJ"]
    assert [p.product_id for p in find("queue manager in WebSphere MQ 7.5")] == ["SSFKSJ"]
    assert [p.product_id for p in find("upgrade to Streams 4.1.1.1")] == ["SSCRJU"]
    assert find("configure WebSphere Operational Decision Management") == []
    assert find("the stream of events") == []
