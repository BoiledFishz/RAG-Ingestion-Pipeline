"""Dependency-light BM25 sparse retrieval over persisted Qdrant payloads."""

from __future__ import annotations

import math
import re
from collections import Counter

from rag.ingestion.models import MetadataValue
from rag.ingestion.vector_store import QdrantVectorStore, VectorRecord
from rag.retrieval.contracts import SearchResult
from rag.retrieval.filters import metadata_matches


class BM25Retriever:
    def __init__(
        self,
        *,
        store: QdrantVectorStore,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.store = store
        self.k1 = k1
        self.b = b
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
        limit: int = 10,
        filters: dict[str, MetadataValue] | None = None,
    ) -> list[SearchResult]:
        if not query.strip() or limit <= 0:
            return []
        if not self._records:
            await self.refresh()
        query_terms = self.tokenize(query)
        if not query_terms or not self._records:
            return []

        count = len(self._records)
        scored: list[SearchResult] = []
        for record, frequencies in zip(self._records, self._term_frequencies, strict=True):
            if not metadata_matches(record.metadata, filters):
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
                    )
                )
        return sorted(scored, key=lambda item: item.score, reverse=True)[:limit]
