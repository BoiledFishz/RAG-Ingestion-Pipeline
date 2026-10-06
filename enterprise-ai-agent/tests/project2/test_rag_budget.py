"""Actual legacy SQL attempts must consume the shared Project 2 budget."""

import json
from pathlib import Path

import pytest

from agents.project2.budget import Budget, BudgetExceeded
from agents.project2.rag_process import BudgetConnection, BoundedRAGProcess


ROOT = Path(__file__).resolve().parents[3]


def test_sql_statement_reserves_before_it_starts() -> None:
    import sqlite3

    path = ROOT / ".rag_data/techqa_full.sqlite"
    budget = Budget(attempts=1)
    db = sqlite3.connect(path.resolve().as_uri()+"?mode=ro", uri=True, factory=BudgetConnection)
    db.request_budget = budget
    assert db.execute("SELECT value FROM manifest WHERE key='scope'").fetchone()[0] == "full"
    with pytest.raises(BudgetExceeded):
        db.execute("SELECT value FROM manifest WHERE key='document_count'")
    db.close()
    assert budget.snapshot()["attempts"] == 1


def test_rag_process_accepts_only_query_and_server_budget() -> None:
    config = json.loads((ROOT / "evals/protocol_v0/baseline_v0.config.json").read_text(encoding="utf-8"))
    runtime = BoundedRAGProcess(config["environment"])
    assert runtime.input_fields == frozenset({"query"})
    assert runtime.model == config["environment"]["AGENT_MODEL"]
    assert runtime.active is False


def test_executemany_does_not_hide_multiple_statement_attempts(tmp_path: Path) -> None:
    import sqlite3

    db = sqlite3.connect(tmp_path / "attempt_metadata.sqlite", factory=BudgetConnection)
    db.execute("CREATE TABLE attempt_metadata(value INTEGER)")
    budget = Budget(attempts=1)
    db.request_budget = budget
    with pytest.raises(BudgetExceeded):
        db.executemany("INSERT INTO attempt_metadata VALUES (?)", [(1,), (2,)])
    db.request_budget = None
    assert db.execute("SELECT COUNT(*) FROM attempt_metadata").fetchone()[0] == 1
    db.close()
