"""Retrieval interfaces and results."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from rag.ingestion.models import MetadataValue


@dataclass(frozen=True, slots=True)
class SearchResult:
    text: str
    metadata: dict[str, MetadataValue]
    score: float
    backend: str

    @property
    def chunk_hash(self) -> str:
        return str(self.metadata.get("chunk_hash", ""))

    def with_score(self, score: float, *, backend: str | None = None) -> SearchResult:
        return replace(self, score=score, backend=backend or self.backend)


class Retriever(Protocol):
    async def retrieve(
        self,
        query: str,
        *,
        limit: int = 10,
        filters: dict[str, MetadataValue] | None = None,
    ) -> list[SearchResult]:
        """Retrieve ranked chunks."""
