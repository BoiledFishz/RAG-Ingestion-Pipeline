from __future__ import annotations

from typing import Protocol

from models.schemas import Document


class VectorStore(Protocol):
    async def search(self, query: str, top_k: int) -> list[Document]: ...


class RetrieverTool:
    name = "vector_database_search"
    description = "Search the internal knowledge-base vector index."

    def __init__(self, store: VectorStore, top_k: int = 5) -> None:
        if not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")
        self.store, self.top_k = store, top_k

    async def invoke(self, query: str, top_k: int | None = None) -> list[Document]:
        if not query.strip():
            return []
        limit = self.top_k if top_k is None else top_k
        if not 1 <= limit <= 20:
            raise ValueError("top_k must be between 1 and 20")
        return await self.store.search(query, limit)
