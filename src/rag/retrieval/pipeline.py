"""Concurrent dense+sparse retrieval, fusion, and reranking."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from rag.ingestion.models import MetadataValue
from rag.retrieval.contracts import (
    RetrievalDiagnostics,
    RetrievalMode,
    RetrievalOutcome,
    Retriever,
    SearchResult,
)
from rag.retrieval.fusion import reciprocal_rank_fusion
from rag.retrieval.reranker import LexicalReranker


@dataclass(frozen=True, slots=True)
class RetrievalConfig:
    mode: RetrievalMode = "hybrid"
    candidate_k: int = 30
    rerank_k: int = 20
    final_k: int = 5
    rrf_rank_constant: int = 60
    max_context_tokens: int = 8_000
    max_chunks_per_document: int = 2
    reranker_timeout_seconds: float = 5.0
    relevance_threshold: float = 0.05

    def __post_init__(self) -> None:
        if self.candidate_k <= 0 or self.rerank_k <= 0 or self.final_k <= 0:
            raise ValueError("retrieval k values must be positive")
        if self.final_k > self.rerank_k or self.rerank_k > self.candidate_k:
            raise ValueError("expected final_k <= rerank_k <= candidate_k")
        if self.rrf_rank_constant <= 0:
            raise ValueError("rrf_rank_constant must be positive")
        if self.max_context_tokens <= 0 or self.max_chunks_per_document <= 0:
            raise ValueError("context limits must be positive")


class DenseRetrievalPipeline:
    """Standalone phase-one Dense retrieval pipeline."""

    def __init__(self, *, dense: Retriever, config: RetrievalConfig | None = None) -> None:
        self.dense = dense
        self.config = config or RetrievalConfig(mode="dense")

    async def retrieve(
        self,
        query: str,
        *,
        mode: RetrievalMode = "dense",
        filters: dict[str, MetadataValue] | None = None,
    ) -> RetrievalOutcome:
        if mode != "dense":
            raise ValueError("DenseRetrievalPipeline only supports mode='dense'")
        candidates = await self.dense.retrieve(
            query,
            limit=self.config.candidate_k,
            filters=filters,
        )
        final = candidates[: self.config.final_k]
        return RetrievalOutcome(
            results=final,
            diagnostics=RetrievalDiagnostics(
                mode="dense",
                dense_candidates=len(candidates),
                final_chunks=len(final),
            ),
        )


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
