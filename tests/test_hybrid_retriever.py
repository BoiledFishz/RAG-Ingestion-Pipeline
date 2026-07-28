from __future__ import annotations

import asyncio

from rag.ingestion.models import MetadataValue
from rag.retrieval.contracts import SearchResult
from rag.retrieval.pipeline import HybridRetriever


class StubRetriever:
    def __init__(self, results: list[SearchResult]) -> None:
        self.results = results

    async def retrieve(
        self,
        query: str,
        *,
        limit: int = 10,
        filters: dict[str, MetadataValue] | None = None,
    ) -> list[SearchResult]:
        return self.results[:limit]


def test_hybrid_fusion_rewards_results_seen_by_both_retrievers() -> None:
    shared = {"chunk_hash": "shared", "source_file": "a.md", "page_number": 1}
    dense = StubRetriever(
        [
            SearchResult("dense only", {"chunk_hash": "dense"}, 0.9, "dense"),
            SearchResult("shared result", shared, 0.8, "dense"),
        ]
    )
    sparse = StubRetriever(
        [
            SearchResult("shared result", shared, 5.0, "sparse"),
            SearchResult("sparse only", {"chunk_hash": "sparse"}, 4.0, "sparse"),
        ]
    )
    results = asyncio.run(HybridRetriever(dense=dense, sparse=sparse).retrieve("query", limit=3))
    assert results[0].chunk_hash == "shared"
