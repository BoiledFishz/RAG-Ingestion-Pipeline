from fastapi.testclient import TestClient
from rag.techqa.data import questions

from api.main import app
from models.errors import ModelUnavailable


def test_critic_rejects_unknown_or_oversized_source_context_before_model_call():
    evidence = "[1] " + questions("fixture")[0]["ANSWER"]
    with TestClient(app) as client:
        for context in ({"7": {"title": "Unknown"}},
                        {"1": {"title": "x" * 201}},
                        {"1": {"applicability": "x" * 501}}):
            response = client.post("/v1/critic-loop", json={
                "task": "Review this official answer", "evidence": evidence,
                "source_context": context,
            })
            assert response.status_code == 422


def test_model_outage_returns_503_instead_of_a_successful_refusal(monkeypatch):
    from api import main

    class UnavailableAgent:
        async def run(self, query):
            raise ModelUnavailable("Injected outage")

    monkeypatch.setattr(main, "build_rag", lambda: UnavailableAgent())
    with TestClient(app) as client:
        response = client.post("/v1/rag/query", json={
            "query": questions("fixture")[0]["QUESTION_TITLE"],
        })
    assert response.status_code == 503
    assert "answer" not in response.json()


def test_critic_caught_network_failure_still_returns_503(monkeypatch):
    import httpx
    from rag.techqa.data import question_text

    from agents.critic import CriticLoop, LLMCritic, LLMGroundedDiagnosisAgent
    from api import main
    from models.llm import MeteredModel

    class Disconnected:
        async def generate(self, prompt, schema):
            raise httpx.ConnectError("Injected local model disconnection")

    meter = MeteredModel(Disconnected())
    critic = CriticLoop(LLMGroundedDiagnosisAgent(meter), LLMCritic(meter), meter)
    monkeypatch.setattr(main, "build_advanced", lambda *_: (meter, None, None, critic))
    row = questions("fixture")[0]
    with TestClient(app) as client:
        response = client.post("/v1/critic-loop", json={
            "task": question_text(row), "evidence": "[1] " + row["ANSWER"],
        })
    assert response.status_code == 503
    assert meter.metrics.llm_calls == 1
    assert "final_diagnosis" not in response.json()
