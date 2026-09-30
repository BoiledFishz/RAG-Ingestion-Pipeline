from __future__ import annotations

from models.schemas import Document
from vectorstore.memory import MemoryVectorStore


class RetrieverTool:
    name = "vector_database_search"
    description = "Search the internal knowledge-base vector index."

    def __init__(self, store: MemoryVectorStore, top_k: int = 5) -> None:
        self.store, self.top_k = store, top_k

    async def invoke(self, query: str, top_k: int | None = None) -> list[Document]:
        if not query.strip():
            return []
        limit = top_k or self.top_k
        if not 1 <= limit <= 20:
            raise ValueError("top_k must be between 1 and 20")
        return await self.store.search(query, limit)
