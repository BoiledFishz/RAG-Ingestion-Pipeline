"""Dense vector retrieval."""

from __future__ import annotations

from rag.ingestion.models import MetadataValue
from rag.ingestion.providers import EmbeddingProvider
from rag.ingestion.vector_store import QdrantVectorStore
from rag.retrieval.contracts import SearchResult
from rag.retrieval.filters import FilterPolicy


class DenseRetriever:
    def __init__(
        self,
        *,
        embedder: EmbeddingProvider,
        store: QdrantVectorStore,
        candidate_k: int = 30,
        final_k: int = 5,
        filter_policy: FilterPolicy | None = None,
    ) -> None:
        if candidate_k <= 0 or final_k <= 0:
            raise ValueError("candidate_k and final_k must be positive")
        if final_k > candidate_k:
            raise ValueError("final_k cannot exceed candidate_k")
        self.embedder = embedder
        self.store = store
        self.candidate_k = candidate_k
        self.final_k = final_k
        self.filter_policy = filter_policy or FilterPolicy()

    async def retrieve(
        self,
        query: str,
        *,
        limit: int | None = None,
        filters: dict[str, MetadataValue] | None = None,
    ) -> list[SearchResult]:
        final_limit = self.final_k if limit is None else limit
        if not query.strip() or final_limit <= 0:
            return []
        candidate_limit = max(self.candidate_k, final_limit)
        secured_filters = self.filter_policy.apply(filters)
        vector = await self.embedder.embed_query(query)
        records = await self.store.search(
            vector,
            limit=candidate_limit,
            filters=secured_filters,
        )
        return [
            SearchResult(
                text=record.text,
                metadata=record.metadata,
                score=record.score,
                backend="dense",
                retrieval_rank=rank,
                retrieval_score=record.score,
                dense_rank=rank,
                retrieval_sources=("dense",),
            )
            for rank, record in enumerate(records, start=1)
        ][:final_limit]
