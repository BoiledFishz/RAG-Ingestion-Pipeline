"""Shared metadata-filter behavior for local sparse retrieval."""

from __future__ import annotations

from rag.ingestion.models import MetadataValue


def metadata_matches(
    metadata: dict[str, MetadataValue], filters: dict[str, MetadataValue] | None
) -> bool:
    if not filters:
        return True
    return all(metadata.get(key) == value for key, value in filters.items())
