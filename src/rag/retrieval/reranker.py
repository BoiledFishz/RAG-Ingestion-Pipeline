"""Fast deterministic reranker; replaceable with a cross-encoder in production."""

from __future__ import annotations

from rag.retrieval.contracts import SearchResult
from rag.retrieval.sparse import BM25Retriever


class LexicalReranker:
    def __init__(self, *, lexical_weight: float = 0.7) -> None:
        if not 0 <= lexical_weight <= 1:
            raise ValueError("lexical_weight must be between 0 and 1")
        self.lexical_weight = lexical_weight

    async def rerank(
        self, query: str, candidates: list[SearchResult], *, limit: int = 5
    ) -> list[SearchResult]:
        query_terms = set(BM25Retriever.tokenize(query))
        if not query_terms:
            return candidates[:limit]
        max_original = max((item.score for item in candidates), default=1.0) or 1.0
        rescored: list[SearchResult] = []
        for item in candidates:
            document_terms = set(BM25Retriever.tokenize(item.text))
            lexical = len(query_terms.intersection(document_terms)) / len(query_terms)
            original = item.score / max_original
            score = self.lexical_weight * lexical + (1 - self.lexical_weight) * original
            rescored.append(item.with_score(score, backend="hybrid+rerank"))
        return sorted(rescored, key=lambda item: item.score, reverse=True)[:limit]
