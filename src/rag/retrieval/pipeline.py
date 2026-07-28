"""Concurrent dense+sparse retrieval, fusion, and reranking."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from rag.ingestion.models import MetadataValue
from rag.retrieval.contracts import (
    RetrievalDiagnostics,
    RetrievalMode,
    RetrievalOutcome,
    Retriever,
    SearchResult,
)
from rag.retrieval.filters import FilterPolicy
from rag.retrieval.fusion import reciprocal_rank_fusion
from rag.retrieval.reranker import BaseReranker, LexicalReranker

LOGGER = logging.getLogger(__name__)


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


class DenseRerankPipeline(DenseRetrievalPipeline):
    """Standalone phase-two Dense retrieval plus bounded reranking."""

    def __init__(
        self,
        *,
        dense: Retriever,
        reranker: BaseReranker,
        config: RetrievalConfig | None = None,
    ) -> None:
        super().__init__(dense=dense, config=config)
        self.reranker = reranker

    async def retrieve(
        self,
        query: str,
        *,
        mode: RetrievalMode = "dense",
        filters: dict[str, MetadataValue] | None = None,
    ) -> RetrievalOutcome:
        if mode != "dense":
            raise ValueError("DenseRerankPipeline only supports mode='dense'")
        candidates = await self.dense.retrieve(
            query,
            limit=self.config.candidate_k,
            filters=filters,
        )
        if not candidates:
            return RetrievalOutcome(
                results=[],
                diagnostics=RetrievalDiagnostics(mode="dense"),
            )

        bounded = candidates[: self.config.rerank_k]
        fallback = False
        try:
            reranked = await asyncio.wait_for(
                self.reranker.rerank(
                    query,
                    bounded,
                    limit=self.config.rerank_k,
                ),
                timeout=self.config.reranker_timeout_seconds,
            )
        except (TimeoutError, Exception):
            fallback = True
            reranked = bounded
            LOGGER.exception(
                "Reranker failed or timed out; falling back to Dense ordering"
            )

        final = reranked[: self.config.final_k]
        return RetrievalOutcome(
            results=final,
            diagnostics=RetrievalDiagnostics(
                mode="dense",
                dense_candidates=len(candidates),
                reranked_candidates=0 if fallback else len(reranked),
                final_chunks=len(final),
                reranker_fallback=fallback,
            ),
        )


class RetrievalPipeline:
    """Production Dense/Sparse/Hybrid retrieval with branch and reranker fallback."""

    def __init__(
        self,
        *,
        dense: Retriever,
        sparse: Retriever,
        reranker: BaseReranker | None = None,
        config: RetrievalConfig | None = None,
        filter_policy: FilterPolicy | None = None,
    ) -> None:
        self.dense = dense
        self.sparse = sparse
        self.reranker = reranker
        self.config = config or RetrievalConfig()
        self.filter_policy = filter_policy or FilterPolicy()

    async def retrieve(
        self,
        query: str,
        *,
        mode: RetrievalMode = "hybrid",
        filters: dict[str, MetadataValue] | None = None,
    ) -> RetrievalOutcome:
        if mode not in {"dense", "sparse", "hybrid"}:
            raise ValueError(f"Unsupported retrieval mode: {mode}")
        secured_filters = self.filter_policy.apply(filters)

        dense_results: list[SearchResult] = []
        sparse_results: list[SearchResult] = []
        if mode == "dense":
            dense_results = await self._safe_retrieve(
                self.dense,
                "Dense",
                query,
                secured_filters,
            )
            candidates = dense_results
        elif mode == "sparse":
            sparse_results = await self._safe_retrieve(
                self.sparse,
                "Sparse",
                query,
                secured_filters,
            )
            candidates = sparse_results
        else:
            dense_value, sparse_value = await asyncio.gather(
                self._safe_retrieve(
                    self.dense,
                    "Dense",
                    query,
                    secured_filters,
                ),
                self._safe_retrieve(
                    self.sparse,
                    "Sparse",
                    query,
                    secured_filters,
                ),
            )
            dense_results = dense_value
            sparse_results = sparse_value
            candidates = reciprocal_rank_fusion(
                [dense_results, sparse_results],
                rank_constant=self.config.rrf_rank_constant,
                limit=self.config.candidate_k,
            )

        reranked, reranker_fallback, reranked_count = await self._rerank(
            query,
            candidates,
        )
        final = reranked[: self.config.final_k]
        return RetrievalOutcome(
            results=final,
            diagnostics=RetrievalDiagnostics(
                mode=mode,
                dense_candidates=len(dense_results),
                sparse_candidates=len(sparse_results),
                reranked_candidates=reranked_count,
                final_chunks=len(final),
                reranker_fallback=reranker_fallback,
            ),
        )

    async def _safe_retrieve(
        self,
        retriever: Retriever,
        label: str,
        query: str,
        filters: dict[str, MetadataValue],
    ) -> list[SearchResult]:
        try:
            return await retriever.retrieve(
                query,
                limit=self.config.candidate_k,
                filters=filters,
            )
        except Exception:
            LOGGER.exception("%s retrieval failed; continuing with available branch", label)
            return []

    async def _rerank(
        self,
        query: str,
        candidates: list[SearchResult],
    ) -> tuple[list[SearchResult], bool, int]:
        if not candidates or self.reranker is None:
            return candidates, False, 0
        bounded = candidates[: self.config.rerank_k]
        try:
            reranked = await asyncio.wait_for(
                self.reranker.rerank(
                    query,
                    bounded,
                    limit=self.config.rerank_k,
                ),
                timeout=self.config.reranker_timeout_seconds,
            )
            return reranked, False, len(reranked)
        except Exception:
            LOGGER.exception(
                "Reranker failed or timed out after fusion; using pre-rerank order"
            )
            return bounded, True, 0


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
