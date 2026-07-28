"""Typed domain objects shared by ingestion components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeAlias

MetadataValue: TypeAlias = str | int | float | bool


@dataclass(frozen=True, slots=True)
class ParsedPage:
    """Text extracted from one logical document page."""

    text: str
    source_file: str
    page_number: int
    used_ocr: bool = False


@dataclass(frozen=True, slots=True)
class Chunk:
    """A text chunk and the metadata persisted alongside its vector."""

    text: str
    metadata: dict[str, MetadataValue]

    @property
    def chunk_hash(self) -> str:
        return str(self.metadata["chunk_hash"])


@dataclass(slots=True)
class IngestionStats:
    """Counters returned by a pipeline run for observability and automation."""

    files_seen: int = 0
    files_succeeded: int = 0
    files_failed: int = 0
    pages_parsed: int = 0
    chunks_created: int = 0
    chunks_skipped: int = 0
    chunks_upserted: int = 0
    warnings: list[str] = field(default_factory=list)
