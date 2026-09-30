from __future__ import annotations

import asyncio

import pytest
from conftest import techqa_fixture
from pydantic import ValidationError

from agents.rag_agent.service import RAGAgent
from models.errors import DependencyUnavailable
from models.providers import HashEmbedder
from models.schemas import Document, MetadataValue, RetrieverInput
from tools.retriever import RetrieverTool
from vectorstore.qdrant import QdrantStore


def test_vector_search_real_qdrant_and_security(
    agent_bundle: tuple[RAGAgent, QdrantStore],
) -> None:
    agent, _ = agent_bundle
    rows = asyncio.run(
        agent.retriever.invoke(
            RetrieverInput(
                query="WebSphere ADMU0111E startup troubleshooting",
                top_k=3,
                filters={"status": "draft"},
            )
        )
    )
    assert 0 < len(rows) <= 3
    assert all(row.metadata["status"] == "published" for row in rows)
    assert all(row.chunk_id != "draft-secret" for row in rows)


def test_tool_filters_and_schema_are_bounded() -> None:
    with pytest.raises(ValidationError):
        RetrieverInput(query="hello", top_k=1000)
    with pytest.raises(ValueError, match="Unsupported"):
        RetrieverTool.secure_filters({"tenant_id": "another-tenant"})
    with pytest.raises(ValueError, match="nonblank strings"):
        RetrieverTool.secure_filters({"source_file": 0.5})


class SlowStore:
    async def search(
        self,
        vector: list[float],
        *,
        limit: int,
        filters: dict[str, MetadataValue],
        embedding_id: str,
        title_query: str | None = None,
    ) -> list[Document]:
        await asyncio.sleep(0.1)
        return []


def test_tool_timeout_is_error_not_no_results() -> None:
    tool = RetrieverTool(SlowStore(), HashEmbedder(), timeout=0.001)
    with pytest.raises(DependencyUnavailable):
        asyncio.run(tool.invoke(RetrieverInput(query="WebSphere startup")))


class NoEmbeddingExpected(HashEmbedder):
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise AssertionError("already-indexed texts must not be embedded again")


def test_seed_is_idempotent_before_embedding(
    agent_bundle: tuple[RAGAgent, QdrantStore],
) -> None:
    _, store = agent_bundle
    assert asyncio.run(store.seed(techqa_fixture(), NoEmbeddingExpected())) == 0


def test_missing_index_is_not_silently_treated_as_no_knowledge() -> None:
    async def scenario() -> None:
        store = QdrantStore("missing")
        try:
            with pytest.raises(DependencyUnavailable):
                await RetrieverTool(store, HashEmbedder()).invoke(
                    RetrieverInput(query="WebSphere startup")
                )
        finally:
            await store.close()

    asyncio.run(scenario())


def test_version_retrieval_adds_bounded_candidates_with_identical_security_filters() -> None:
    class VersionStore:
        calls: list[tuple[int, dict[str, MetadataValue], str | None]] = []

        async def search(self, vector, *, limit, filters, embedding_id, title_query=None):
            self.calls.append((limit, filters, title_query))
            precise = title_query is not None
            return [Document(
                chunk_id="correct" if precise else "noise", source_file="technote",
                text=("Streams 4.1.1.2 requires bashrc changes."
                      if precise else "Environment variables"),
                metadata={"status": "published", "language": "en", "title":
                          "User environment variables after upgrading Streams 4.1.1.2" if precise
                          else "Unrelated environment variables"},
            )]

    store = VersionStore()
    result = asyncio.run(RetrieverTool(store, HashEmbedder()).invoke(RetrieverInput(
        query="User environment variables after upgrading Streams 4.1.1.2", top_k=1,
        filters={"language": "en", "status": "draft"},
    )))
    assert result[0].chunk_id == "correct"
    assert len(store.calls) == 2
    assert all(filters == {"language": "en", "status": "published"}
               for _, filters, _ in store.calls)
    assert store.calls[1][0] == 4
    assert store.calls[1][2] == "Streams 4.1.1.2"
