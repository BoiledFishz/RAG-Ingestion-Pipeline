"""Versioned API enforcement contracts using original official requests."""

import asyncio
import json
from pathlib import Path

from fastapi.testclient import TestClient

from agents.project2.budget import Budget
from agents.project2.policy import TrustedContext
from api.project2_main import create_app

ROOT = Path(__file__).resolve().parents[3]


def original_query() -> str:
    rows = json.loads((ROOT / "specs/project2/v0.2/task_preregistration.json").read_text(encoding="utf-8"))["samples"]
    return next(x["query"] for x in rows if x["sample_id"] == "P2-ENTITY-01")


def test_default_route_has_server_auth_and_no_budget_bypass() -> None:
    owner = TrustedContext("test-owner", "local", frozenset({"full"}), frozenset({"document_count", "rag_explain"}))
    app = create_app(credentials={"test-credential": owner}, warmup=False)
    client = TestClient(app)
    denied = client.post("/v1/project2/analysis", json={"query": original_query()}).json()
    assert denied["status"] == "permission_denied"
    assert denied["usage"]["attempts"] == 0
    invalid = client.post("/v1/project2/analysis", headers={"Authorization": "Bearer test-credential"}, json={"query": original_query(), "subject_id": "self-granted"})
    assert invalid.json()["status"] == "failed"
    assert invalid.json()["usage"]["attempts"] == 0
    assert all(route.path != "/v1/worker/database" for route in app.routes)


def test_independent_legal_db_can_run_if_rag_denied() -> None:
    owner = TrustedContext("test-owner", "local", frozenset({"full"}), frozenset({"document_count"}))
    client = TestClient(create_app(credentials={"test-credential": owner}, warmup=False))
    result = client.post("/v1/project2/analysis", headers={"Authorization": "Bearer test-credential"}, json={"query": original_query()}).json()
    assert result["workers"]["database"]["status"] == "completed"
    assert result["workers"]["rag"]["status"] == "permission_denied"
    assert result["status"] == "partial"
    assert result["usage"]["llm_calls"] == 0
