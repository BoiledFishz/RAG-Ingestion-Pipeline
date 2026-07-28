"""Concurrent dense+sparse retrieval, fusion, and reranking."""

from __future__ import annotations

import asyncio

from rag.ingestion.models import MetadataValue
from rag.retrieval.contracts import Retriever, SearchResult
from rag.retrieval.fusion import reciprocal_rank_fusion
from rag.retrieval.reranker import LexicalReranker


class HybridRetriever:
    def __init__(
        self,
        *,
        dense: Retriever,
        sparse: Retriever,
        reranker: LexicalReranker | None = None,
        candidate_multiplier: int = 3,
    ) -> None:
        self.dense = dense
        self.sparse = sparse
        self.reranker = reranker
        self.candidate_multiplier = candidate_multiplier

    async def retrieve(
        self,
        query: str,
        *,
        limit: int = 5,
        filters: dict[str, MetadataValue] | None = None,
    ) -> list[SearchResult]:
        candidate_limit = max(limit * self.candidate_multiplier, limit)
        dense_results, sparse_results = await asyncio.gather(
            self.dense.retrieve(query, limit=candidate_limit, filters=filters),
            self.sparse.retrieve(query, limit=candidate_limit, filters=filters),
        )
        fused = reciprocal_rank_fusion([dense_results, sparse_results], limit=candidate_limit)
        if self.reranker:
            return await self.reranker.rerank(query, fused, limit=limit)
        return fused[:limit]
