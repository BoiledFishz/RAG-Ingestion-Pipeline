"""Shared metadata-filter behavior for local sparse retrieval."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from rag.ingestion.models import MetadataValue

LOGGER = logging.getLogger(__name__)
SUPPORTED_USER_FILTERS = frozenset({"source_file", "document_type", "language", "status"})


@dataclass(frozen=True, slots=True)
class FilterPolicy:
    """Merge user filters with non-overridable system security conditions."""

    system_filters: dict[str, MetadataValue] = field(
        default_factory=lambda: {"status": "published"}
    )
    allowed_user_filters: frozenset[str] = SUPPORTED_USER_FILTERS

    def apply(
        self, user_filters: dict[str, MetadataValue] | None
    ) -> dict[str, MetadataValue]:
        supplied = user_filters or {}
        unknown = set(supplied).difference(self.allowed_user_filters).difference(
            self.system_filters
        )
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"Unsupported metadata filter(s): {names}")

        merged = {
            key: value
            for key, value in supplied.items()
            if key not in self.system_filters
        }
        for key, value in self.system_filters.items():
            if key in supplied and supplied[key] != value:
                LOGGER.warning(
                    "Ignored attempt to override system metadata filter %s=%r",
                    key,
                    value,
                )
            merged[key] = value
        return merged


def metadata_matches(
    metadata: dict[str, MetadataValue], filters: dict[str, MetadataValue] | None
) -> bool:
    if not filters:
        return True
    return all(metadata.get(key) == value for key, value in filters.items())
