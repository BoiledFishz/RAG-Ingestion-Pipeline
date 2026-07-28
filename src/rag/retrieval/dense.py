"""Dense vector retrieval."""

from __future__ import annotations

from rag.ingestion.models import MetadataValue
from rag.ingestion.providers import EmbeddingProvider
from rag.ingestion.vector_store import QdrantVectorStore
from rag.retrieval.contracts import SearchResult


class DenseRetriever:
    def __init__(self, *, embedder: EmbeddingProvider, store: QdrantVectorStore) -> None:
        self.embedder = embedder
        self.store = store

    async def retrieve(
        self,
        query: str,
        *,
        limit: int = 10,
        filters: dict[str, MetadataValue] | None = None,
    ) -> list[SearchResult]:
        if not query.strip() or limit <= 0:
            return []
        vector = await self.embedder.embed_query(query)
        records = await self.store.search(vector, limit=limit, filters=filters)
        return [
            SearchResult(
                text=record.text,
                metadata=record.metadata,
                score=record.score,
                backend="dense",
            )
            for record in records
        ]
