"""Retrieval interfaces and results."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal, Protocol

from rag.ingestion.models import MetadataValue

RetrievalMode = Literal["dense", "sparse", "hybrid"]


@dataclass(frozen=True, slots=True)
class SearchResult:
    text: str
    metadata: dict[str, MetadataValue]
    score: float
    backend: str
    retrieval_rank: int | None = None
    retrieval_score: float | None = None
    dense_rank: int | None = None
    sparse_rank: int | None = None
    fusion_rank: int | None = None
    rerank_rank: int | None = None
    rerank_score: float | None = None
    retrieval_sources: tuple[str, ...] = ()

    @property
    def chunk_hash(self) -> str:
        return str(self.metadata.get("chunk_hash", ""))

    @property
    def chunk_id(self) -> str:
        return str(self.metadata.get("chunk_id") or self.chunk_hash)

    @property
    def source_file(self) -> str:
        return str(self.metadata.get("source_file", ""))

    @property
    def page_number(self) -> int | str:
        value = self.metadata.get("page_number", "?")
        return value if isinstance(value, (int, str)) else "?"

    @property
    def document_type(self) -> str:
        return str(self.metadata.get("document_type", ""))

    @property
    def language(self) -> str:
        return str(self.metadata.get("language", ""))

    @property
    def status(self) -> str:
        return str(self.metadata.get("status", ""))

    def to_dict(self) -> dict[str, object]:
        """Serialize required retrieval fields at the top level for API adapters."""

        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_file": self.source_file,
            "page_number": self.page_number,
            "retrieval_score": self.retrieval_score,
            "retrieval_rank": self.retrieval_rank,
            "dense_rank": self.dense_rank,
            "sparse_rank": self.sparse_rank,
            "fusion_rank": self.fusion_rank,
            "rerank_rank": self.rerank_rank,
            "rerank_score": self.rerank_score,
            "retrieval_sources": list(self.retrieval_sources),
            "metadata": dict(self.metadata),
        }

    def with_score(self, score: float, *, backend: str | None = None) -> SearchResult:
        return replace(self, score=score, backend=backend or self.backend)


@dataclass(frozen=True, slots=True)
class RetrievalDiagnostics:
    mode: RetrievalMode
    dense_candidates: int = 0
    sparse_candidates: int = 0
    reranked_candidates: int = 0
    final_chunks: int = 0
    context_tokens: int = 0
    reranker_fallback: bool = False


@dataclass(frozen=True, slots=True)
class RetrievalOutcome:
    results: list[SearchResult]
    diagnostics: RetrievalDiagnostics


class Retriever(Protocol):
    async def retrieve(
        self,
        query: str,
        *,
        limit: int = 10,
        filters: dict[str, MetadataValue] | None = None,
    ) -> list[SearchResult]:
        """Retrieve ranked chunks."""


class RetrievalEngine(Protocol):
    async def retrieve(
        self,
        query: str,
        *,
        mode: RetrievalMode = "dense",
        filters: dict[str, MetadataValue] | None = None,
    ) -> RetrievalOutcome:
        """Execute one configured retrieval mode."""


class ParentResolver(Protocol):
    async def retrieve_by_chunk_ids(self, chunk_ids: list[str]) -> list[SearchResult]:
        """Retrieve parent chunks after final ranking."""
