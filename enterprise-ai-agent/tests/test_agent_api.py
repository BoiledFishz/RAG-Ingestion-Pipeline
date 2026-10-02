from __future__ import annotations

import asyncio

import httpx

from agents.rag_agent.service import RAGAgent
from api.main import create_app
from models.errors import DependencyUnavailable
from models.schemas import Evidence, SelectionDraft
from vectorstore.qdrant import QdrantStore


def test_agent_api_contract_and_unicode(
    agent_bundle: tuple[RAGAgent, QdrantStore],
) -> None:
    agent, _ = agent_bundle

    async def scenario() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(agent)),
            base_url="http://test",
        ) as client:
            response = await client.post("/v1/agent/query", json={"query": "权限有问题，怎么办？"})
            assert response.status_code == 200
            assert "charset=utf-8" in response.headers["content-type"]
            assert "请补充" in response.content.decode("utf-8")
            assert set(response.json()) == {"answer", "sources", "confidence"}
            assert (await client.get("/healthz")).status_code == 200

    asyncio.run(scenario())


def test_agent_api_rejects_blank_extra_fields_and_unknown_filters(
    agent_bundle: tuple[RAGAgent, QdrantStore],
) -> None:
    agent, _ = agent_bundle

    async def scenario() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(agent)),
            base_url="http://test",
        ) as client:
            assert (await client.post("/v1/agent/query", json={"query": "   "})).status_code == 422
            assert (
                await client.post(
                    "/v1/agent/query",
                    json={"query": "hello", "secret": "x"},
                )
            ).status_code == 422
            assert (
                await client.post(
                    "/v1/agent/query",
                    json={
                        "query": "WebSphere startup error",
                        "filters": {"tenant_id": "x"},
                    },
                )
            ).status_code == 400

    asyncio.run(scenario())


def test_agent_api_reports_model_outage_as_503(
    agent_bundle: tuple[RAGAgent, QdrantStore],
) -> None:
    class UnavailableSelector:
        async def select(
            self,
            query: str,
            evidence: list[Evidence],
            correction: str = "",
        ) -> SelectionDraft:
            raise DependencyUnavailable("model offline")

    agent, _ = agent_bundle
    agent.selector = UnavailableSelector()

    async def scenario() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(agent)),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/v1/agent/query",
                json={
                    "query": "How are Streams environment variables set after upgrade to 4.1.1.2?",
                },
            )
            assert response.status_code == 503

    asyncio.run(scenario())
