"""Dependency-light BM25 sparse retrieval over persisted Qdrant payloads."""

from __future__ import annotations

import math
import re
from collections import Counter

from rag.ingestion.models import MetadataValue
from rag.ingestion.vector_store import QdrantVectorStore, VectorRecord
from rag.retrieval.contracts import SearchResult
from rag.retrieval.filters import FilterPolicy, metadata_matches


class BM25Retriever:
    def __init__(
        self,
        *,
        store: QdrantVectorStore,
        k1: float = 1.5,
        b: float = 0.75,
        candidate_k: int = 30,
        final_k: int = 5,
        filter_policy: FilterPolicy | None = None,
    ) -> None:
        if candidate_k <= 0 or final_k <= 0:
            raise ValueError("candidate_k and final_k must be positive")
        if final_k > candidate_k:
            raise ValueError("final_k cannot exceed candidate_k")
        self.store = store
        self.k1 = k1
        self.b = b
        self.candidate_k = candidate_k
        self.final_k = final_k
        self.filter_policy = filter_policy or FilterPolicy()
        self._records: list[VectorRecord] = []
        self._term_frequencies: list[Counter[str]] = []
        self._document_frequencies: Counter[str] = Counter()
        self._average_length = 0.0

    @staticmethod
    def tokenize(text: str) -> list[str]:
        latin = re.findall(r"[a-z0-9][a-z0-9_.:/-]*", text.lower())
        chinese = re.findall(r"[\u4e00-\u9fff]", text)
        chinese_bigrams = ["".join(chinese[index : index + 2]) for index in range(len(chinese) - 1)]
        return latin + chinese + chinese_bigrams

    async def refresh(self) -> None:
        self.fit(await self.store.list_records())

    def fit(self, records: list[VectorRecord]) -> None:
        self._records = records
        self._term_frequencies = [Counter(self.tokenize(record.text)) for record in records]
        self._document_frequencies = Counter()
        for frequencies in self._term_frequencies:
            self._document_frequencies.update(frequencies.keys())
        total_length = sum(sum(frequencies.values()) for frequencies in self._term_frequencies)
        self._average_length = total_length / len(records) if records else 0.0

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
        if not self._records:
            await self.refresh()
        query_terms = self.tokenize(query)
        if not query_terms or not self._records:
            return []

        count = len(self._records)
        scored: list[SearchResult] = []
        for record, frequencies in zip(self._records, self._term_frequencies, strict=True):
            if not metadata_matches(record.metadata, secured_filters):
                continue
            document_length = sum(frequencies.values())
            score = 0.0
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                document_frequency = self._document_frequencies[term]
                inverse_frequency = math.log(
                    1 + (count - document_frequency + 0.5) / (document_frequency + 0.5)
                )
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * document_length / max(self._average_length, 1.0)
                )
                score += inverse_frequency * frequency * (self.k1 + 1) / denominator
            if score > 0:
                scored.append(
                    SearchResult(
                        text=record.text,
                        metadata=record.metadata,
                        score=score,
                        backend="sparse",
                        retrieval_score=score,
                        retrieval_sources=("sparse",),
                    )
                )
        ordered = sorted(scored, key=lambda item: item.score, reverse=True)[:candidate_limit]
        return [
            SearchResult(
                text=item.text,
                metadata=item.metadata,
                score=item.score,
                backend=item.backend,
                retrieval_rank=rank,
                retrieval_score=item.retrieval_score,
                sparse_rank=rank,
                retrieval_sources=item.retrieval_sources,
            )
            for rank, item in enumerate(ordered, start=1)
        ][:final_limit]
