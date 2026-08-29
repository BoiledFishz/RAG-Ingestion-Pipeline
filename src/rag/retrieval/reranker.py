"""Isolated reranker interfaces and local explainable/model adapters."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import replace
from typing import Protocol, cast

from rag.retrieval.contracts import SearchResult
from rag.retrieval.sparse import BM25Retriever

LOGGER = logging.getLogger(__name__)


class BaseReranker(Protocol):
    async def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        *,
        limit: int,
    ) -> list[SearchResult]:
        """Rerank only the bounded candidate set returned by retrieval."""


class CrossEncoderScorer(Protocol):
    def predict(
        self,
        sentences: list[tuple[str, str]],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> Sequence[float]:
        """Return one relevance score for each query/document pair."""


class LexicalReranker:
    """Explainable local reranker over chunk text plus context_summary."""

    def __init__(self, *, lexical_weight: float = 0.7) -> None:
        if not 0 <= lexical_weight <= 1:
            raise ValueError("lexical_weight must be between 0 and 1")
        self.lexical_weight = lexical_weight

    async def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        *,
        limit: int = 5,
    ) -> list[SearchResult]:
        if not candidates or limit <= 0:
            return []
        query_terms = set(BM25Retriever.tokenize(query))
        if not query_terms:
            return [
                replace(
                    item,
                    rerank_rank=rank,
                    rerank_score=item.score,
                )
                for rank, item in enumerate(candidates[:limit], start=1)
            ]

        max_original = max((abs(item.score) for item in candidates), default=1.0) or 1.0
        rescored: list[SearchResult] = []
        for item in candidates:
            summary = str(item.metadata.get("context_summary", ""))
            document_terms = set(BM25Retriever.tokenize(f"{summary}\n{item.text}"))
            lexical = len(query_terms.intersection(document_terms)) / len(query_terms)
            original = max(0.0, item.score / max_original)
            score = self.lexical_weight * lexical + (1 - self.lexical_weight) * original
            rescored.append(
                replace(
                    item,
                    score=score,
                    backend=f"{item.backend}+rerank",
                    rerank_score=score,
                )
            )

        ordered = sorted(rescored, key=lambda item: item.score, reverse=True)[:limit]
        return [
            replace(item, rerank_rank=rank)
            for rank, item in enumerate(ordered, start=1)
        ]


class CrossEncoderReranker:
    """Local sentence-transformers CrossEncoder adapter with lazy model loading."""

    def __init__(
        self,
        *,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        batch_size: int = 16,
        model: CrossEncoderScorer | None = None,
    ) -> None:
        if not model_name.strip():
            raise ValueError("model_name cannot be empty")
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        self.model_name = model_name
        self.batch_size = batch_size
        self._model = model

    async def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        *,
        limit: int = 5,
    ) -> list[SearchResult]:
        if not candidates or limit <= 0:
            return []
        if not query.strip():
            return candidates[:limit]
        scores = await asyncio.to_thread(self._predict, query, candidates)
        if len(scores) != len(candidates):
            raise ValueError(
                "Cross-encoder returned a different number of scores than candidates"
            )
        rescored = [
            replace(
                candidate,
                score=score,
                backend=f"{candidate.backend}+cross-encoder",
                rerank_score=score,
            )
            for candidate, score in zip(candidates, scores, strict=True)
        ]
        ordered = sorted(rescored, key=lambda item: item.score, reverse=True)[:limit]
        return [replace(item, rerank_rank=rank) for rank, item in enumerate(ordered, start=1)]

    def _predict(self, query: str, candidates: list[SearchResult]) -> list[float]:
        model = self._get_model()
        pairs = [
            (
                query,
                self._candidate_document(candidate),
            )
            for candidate in candidates
        ]
        raw_scores = model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
        )
        return [float(score) for score in raw_scores]

    def _get_model(self) -> CrossEncoderScorer:
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RuntimeError(
                "Install the 'rerank' extra to use the local cross-encoder adapter"
            ) from exc
        LOGGER.info("Loading local cross-encoder model %s", self.model_name)
        self._model = cast(CrossEncoderScorer, CrossEncoder(self.model_name))
        return self._model

    @staticmethod
    def _candidate_document(candidate: SearchResult) -> str:
        summary = str(candidate.metadata.get("context_summary", "")).strip()
        if not summary:
            return candidate.text
        return f"Context summary: {summary}\nChunk: {candidate.text}"


LexicalRerankerAdapter = LexicalReranker
CrossEncoderRerankerAdapter = CrossEncoderReranker
