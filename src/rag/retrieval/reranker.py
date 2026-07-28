"""Isolated reranker interfaces and an explainable local adapter."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from rag.retrieval.contracts import SearchResult
from rag.retrieval.sparse import BM25Retriever


class BaseReranker(Protocol):
    async def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        *,
        limit: int,
    ) -> list[SearchResult]:
        """Rerank only the bounded candidate set returned by retrieval."""


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


LexicalRerankerAdapter = LexicalReranker
