from __future__ import annotations

import hashlib
import json

from fastapi.testclient import TestClient

from agents.chap12.contracts import FinalResponse
from api.chap12_main import create_app, load_credentials

TOKEN = "test-token"
CREDENTIALS = load_credentials(json.dumps({hashlib.sha256(TOKEN.encode()).hexdigest(): {
    "subject_id": "s", "tenant_id": "t", "allowed_workers": ["rag"],
    "allowed_db_operations": [], "allowed_product_ids": ["*"]}}))


class FakeSupervisor:
    def __init__(self) -> None:
        self.contexts: list[object] = []

    async def run(self, request, ctx):  # type: ignore[no-untyped-def]
        self.contexts.append(ctx)
        return FinalResponse(run_id="r", status="no_data", goal=request.goal, plan=[],
                             answer="none", worker_results=[], usage={})


def client() -> tuple[TestClient, FakeSupervisor]:
    fake = FakeSupervisor()
    return TestClient(create_app(lambda: fake, CREDENTIALS)), fake


def test_requires_server_side_credential() -> None:
    api, fake = client()
    assert api.post("/v1/chap12/analyze", json={"query": "x"}).status_code == 401
    assert api.post("/v1/chap12/analyze", json={"query": "x"},
                    headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert fake.contexts == []


def test_body_cannot_grant_rights_or_add_tasks() -> None:
    api, fake = client()
    auth = {"Authorization": f"Bearer {TOKEN}"}
    assert api.post("/v1/chap12/analyze", headers=auth, json={
        "query": "x", "allowed_workers": ["database"]}).status_code == 422
    assert api.post("/v1/chap12/analyze", headers=auth,
                    json={"query": "x", "goal": "publish"}).status_code == 422
    response = api.post("/v1/chap12/analyze", headers=auth, json={"query": "x"})
    assert response.status_code == 200 and response.json()["status"] == "no_data"
    assert fake.contexts[0].allowed_workers == frozenset({"rag"})  # type: ignore[attr-defined]
