"""Parent-node lookup after final child ranking."""

from __future__ import annotations

from rag.ingestion.vector_store import QdrantVectorStore
from rag.retrieval.contracts import SearchResult


class QdrantParentResolver:
    def __init__(self, *, store: QdrantVectorStore) -> None:
        self.store = store

    async def retrieve_by_chunk_ids(self, chunk_ids: list[str]) -> list[SearchResult]:
        records = await self.store.get_by_chunk_ids(chunk_ids)
        return [
            SearchResult(
                text=record.text,
                metadata=record.metadata,
                score=record.score,
                backend="parent",
            )
            for record in records
        ]
