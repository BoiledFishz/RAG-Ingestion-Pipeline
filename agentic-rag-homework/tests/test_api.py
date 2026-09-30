from fastapi.testclient import TestClient

from api.main import app


def test_api_exposes_rag_and_multi_agent_contracts() -> None:
    client = TestClient(app)
    rag = client.post("/v1/rag/query", json={"query": "What is the Lambda timeout range?"})
    assert rag.status_code == 200
    assert set(rag.json()) == {"answer", "sources", "confidence"}

    multi = client.post("/v1/multi-agent", json={"query": "What is the Lambda timeout range?"})
    assert multi.status_code == 200
    assert multi.json()["plan"]["tasks"][0]["agent"] == "research_agent"
    assert multi.json()["critic"]["passed"] is True
