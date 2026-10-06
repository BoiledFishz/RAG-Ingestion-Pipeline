"""Real official counts and policy/budget contracts; no fabricated corpus."""

import asyncio
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from agents.project2.budget import Budget, BudgetExceeded
from agents.project2.policy import TrustedContext
from agents.project2.supervisor import combine_status
from models.project2 import AnalysisRequest
from tools.techqa_document_query import DatabaseWorker


ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "specs/project2/v0.2"
FULL = ROOT / ".rag_data/techqa_full.sqlite"


def owner() -> TrustedContext:
    return TrustedContext("test-owner", "local", frozenset({"full"}), frozenset({"document_count", "compare_document_counts", "list_matching_documents", "rag_explain"}))


def original_sample(key: str) -> dict:
    rows = json.loads((DOCS / "task_preregistration.json").read_text(encoding="utf-8"))["samples"]
    return next(x for x in rows if x["sample_id"] == key)


def test_real_db_is_independent_and_exact() -> None:
    sample = original_sample("P2-ENTITY-01")
    request = AnalysisRequest(query=sample["query"], analysis_operation=sample["analysis_operation"])
    report = json.loads((ROOT / "audit/project2-v1/preflight_report.json").read_text(encoding="utf-8"))
    expected = report["sample_measurements"][sample["sample_id"]]["counts"]
    result = asyncio.run(DatabaseWorker(FULL).run(request, owner(), Budget(), "test-real-db"))
    assert result.status == "completed"
    assert [group["count"] for group in result.payload["groups"]] == expected
    assert result.usage["llm_calls"] == 0


def test_real_zero_not_null() -> None:
    sample = original_sample("P2-VERSION-01")
    zero = json.loads((DOCS / "zero_predicate_registration.json").read_text(encoding="utf-8"))["predicates"][0]
    request = AnalysisRequest(query=sample["query"], analysis_predicates=[zero["phrases"]])
    result = asyncio.run(DatabaseWorker(FULL).run(request, owner(), Budget(), "test-zero"))
    assert result.status == "no_data"
    assert result.payload["groups"][0]["count"] == 0
    assert result.payload["measurement_complete"] is True


def test_real_overlap_and_partial_use_independent_counts() -> None:
    sample = original_sample("P2-COMPARE-03")
    report = json.loads((ROOT / "audit/project2-v1/preflight_report.json").read_text(encoding="utf-8"))
    expected = report["sample_measurements"][sample["sample_id"]]
    request = AnalysisRequest(query=sample["query"], analysis_operation=sample["analysis_operation"])
    result = asyncio.run(DatabaseWorker(FULL).run(request, owner(), Budget(), "test-compare"))
    assert [x["count"] for x in result.payload["groups"]] == expected["counts"]
    assert result.payload["intersection"] == expected["intersection"]
    assert result.payload["delta_a_minus_b"] == expected["delta_a_minus_b"]
    partial = asyncio.run(DatabaseWorker(FULL, inject_timeout_group=1).run(request, owner(), Budget(), "test-partial"))
    assert partial.status == "partial"
    assert partial.payload["groups"][0]["count"] == expected["counts"][0]
    assert partial.payload["groups"][1]["count"] is None
    assert partial.payload["intersection"] is partial.payload["delta_a_minus_b"] is None


def test_real_wrong_scope_fails_with_null() -> None:
    sample = original_sample("P2-ENTITY-01")
    result = asyncio.run(DatabaseWorker(ROOT / ".rag_data/techqa_fixture.sqlite").run(AnalysisRequest(query=sample["query"]), owner(), Budget(), "test-scope"))
    assert result.status == "failed"
    assert result.error["category"] == "data_version_mismatch"
    assert result.payload["measurement_complete"] is False


def test_attempt_17_and_llm_7_never_start() -> None:
    budget = Budget()
    started = []
    for number in range(16):
        budget.reserve("db")
        started.append(number)
    with pytest.raises(BudgetExceeded):
        budget.reserve("db")
        started.append(16)
    assert len(started) == 16
    model_budget = Budget()
    for _ in range(6):
        model_budget.reserve("llm")
    with pytest.raises(BudgetExceeded):
        model_budget.reserve("llm")
    assert model_budget.snapshot()["llm_calls"] == 6


def test_direct_worker_cannot_bypass_budget_or_policy() -> None:
    sample = original_sample("P2-ENTITY-01")
    request = AnalysisRequest(query=sample["query"])
    budget = Budget()
    for _ in range(16):
        budget.reserve("db")
    result = asyncio.run(DatabaseWorker(FULL).run(request, owner(), budget, "test-budget"))
    assert result.status == "timeout"
    denied = TrustedContext("restricted", "local", frozenset(), frozenset())
    fresh = Budget()
    result = asyncio.run(DatabaseWorker(FULL).run(request, denied, fresh, "test-denied"))
    assert result.status == "permission_denied"
    assert fresh.snapshot()["attempts"] == 0


def test_request_preserves_query_and_rejects_oracle_or_sql() -> None:
    raw = original_sample("P2-ENTITY-01")["query"]
    assert AnalysisRequest(query=raw).query == raw
    with pytest.raises(ValidationError):
        AnalysisRequest(query=raw, official_answer="")
    with pytest.raises(ValidationError):
        AnalysisRequest(query=raw, analysis_operation="SELECT 1")


def test_all_36_pairs_match_frozen_matrix() -> None:
    spec = (DOCS / "spec.md").read_text(encoding="utf-8")
    block = spec.split('id="s07"', 1)[1].split('id="s08"', 1)[0]
    lines = [x for x in block.splitlines() if x.startswith("| ")]
    columns = [x.strip() for x in lines[0].strip("|").split("|")][1:]
    tested = 0
    for line in lines[2:]:
        cells = [x.strip() for x in line.strip("|").split("|")]
        for db, expected in zip(columns, cells[1:]):
            assert combine_status(cells[0], db) == expected
            tested += 1
    assert tested == 36
