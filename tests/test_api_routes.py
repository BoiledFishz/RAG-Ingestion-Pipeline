from __future__ import annotations

import asyncio

import httpx

from rag.api.routes import create_app
from rag.generation.service import RAGService
from rag.ingestion.models import MetadataValue
from rag.retrieval.contracts import (
    RetrievalDiagnostics,
    RetrievalMode,
    RetrievalOutcome,
    SearchResult,
)


class APIEngine:
    async def retrieve(
        self,
        query: str,
        *,
        mode: RetrievalMode = "dense",
        filters: dict[str, MetadataValue] | None = None,
    ) -> RetrievalOutcome:
        result = SearchResult(
            "An explicit deny overrides an allow.",
            {
                "chunk_id": "iam-1",
                "chunk_hash": "iam-hash",
                "source_file": "iam.pdf",
                "page_number": 3,
            },
            0.9,
            "hybrid+rerank",
            rerank_score=0.9,
        )
        return RetrievalOutcome(
            [result],
            RetrievalDiagnostics(
                mode=mode,
                dense_candidates=1,
                sparse_candidates=1,
                reranked_candidates=1,
                final_chunks=1,
            ),
        )


class APIGenerator:
    async def generate(
        self,
        *,
        question: str,
        context: str,
        correction: str | None = None,
    ) -> str:
        return "An explicit deny overrides an allow [S1]."


def test_v1_rag_query_contract() -> None:
    async def scenario() -> None:
        app = create_app(
            service=RAGService(
                retriever=APIEngine(),
                generator=APIGenerator(),
            )
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/v1/rag/query",
                json={
                    "query": "What overrides an allow?",
                    "mode": "hybrid",
                    "filters": {"language": "en"},
                },
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["answer"].endswith("[S1].")
        assert payload["citations"] == [
            {
                "source_id": "S1",
                "chunk_id": "iam-1",
                "source_file": "iam.pdf",
                "page_number": 3,
            }
        ]
        assert payload["retrieval"]["mode"] == "hybrid"
        assert payload["refused"] is False

    asyncio.run(scenario())
