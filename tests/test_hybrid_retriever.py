from __future__ import annotations

import asyncio

from rag.ingestion.models import MetadataValue
from rag.retrieval.contracts import SearchResult
from rag.retrieval.fusion import reciprocal_rank_fusion
from rag.retrieval.pipeline import HybridRetriever, RetrievalConfig, RetrievalPipeline


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


def test_rrf_fusion() -> None:
    dense = [
        SearchResult(
            "shared",
            {"chunk_hash": "shared", "chunk_id": "shared"},
            0.9,
            "dense",
            dense_rank=1,
            retrieval_sources=("dense",),
        ),
        SearchResult(
            "dense",
            {"chunk_hash": "dense", "chunk_id": "dense"},
            0.8,
            "dense",
            dense_rank=2,
            retrieval_sources=("dense",),
        ),
    ]
    sparse = [
        SearchResult(
            "sparse",
            {"chunk_hash": "sparse", "chunk_id": "sparse"},
            4.0,
            "sparse",
            sparse_rank=1,
            retrieval_sources=("sparse",),
        ),
        SearchResult(
            "shared",
            {"chunk_hash": "shared", "chunk_id": "shared"},
            3.0,
            "sparse",
            sparse_rank=2,
            retrieval_sources=("sparse",),
        ),
    ]
    fused = reciprocal_rank_fusion([dense, sparse], rank_constant=60, limit=3)
    assert fused[0].chunk_id == "shared"
    assert fused[0].dense_rank == 1
    assert fused[0].sparse_rank == 2
    assert fused[0].fusion_rank == 1
    assert fused[0].retrieval_sources == ("dense", "sparse")


def test_duplicate_chunk_removed() -> None:
    duplicate = SearchResult(
        "same",
        {"chunk_hash": "same", "chunk_id": "same"},
        1.0,
        "dense",
    )
    fused = reciprocal_rank_fusion(
        [[duplicate, duplicate], [duplicate]],
        rank_constant=60,
        limit=10,
    )
    assert len(fused) == 1
    assert fused[0].chunk_id == "same"


class FailingRetriever:
    async def retrieve(
        self,
        query: str,
        *,
        limit: int = 10,
        filters: dict[str, MetadataValue] | None = None,
    ) -> list[SearchResult]:
        raise RuntimeError("simulated branch outage")


class CapturingRetriever(StubRetriever):
    def __init__(self, results: list[SearchResult]) -> None:
        super().__init__(results)
        self.last_filters: dict[str, MetadataValue] | None = None

    async def retrieve(
        self,
        query: str,
        *,
        limit: int = 10,
        filters: dict[str, MetadataValue] | None = None,
    ) -> list[SearchResult]:
        self.last_filters = filters
        return await super().retrieve(query, limit=limit, filters=filters)


def test_hybrid_degrades_to_available_branch_and_shares_filters() -> None:
    sparse = CapturingRetriever(
        [
            SearchResult(
                "S3 evidence",
                {"chunk_hash": "s3", "chunk_id": "s3"},
                3.0,
                "sparse",
                sparse_rank=1,
                retrieval_sources=("sparse",),
            )
        ]
    )
    config = RetrievalConfig(candidate_k=3, rerank_k=2, final_k=1)
    pipeline = RetrievalPipeline(
        dense=FailingRetriever(),
        sparse=sparse,
        config=config,
    )
    outcome = asyncio.run(
        pipeline.retrieve(
            "S3",
            mode="hybrid",
            filters={"status": "draft", "language": "en"},
        )
    )
    assert outcome.results[0].chunk_id == "s3"
    assert outcome.results[0].retrieval_sources == ("sparse",)
    assert sparse.last_filters == {"status": "published", "language": "en"}
