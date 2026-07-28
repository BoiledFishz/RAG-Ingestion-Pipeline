from __future__ import annotations

import asyncio

from rag.ingestion.models import MetadataValue
from rag.retrieval.contracts import SearchResult
from rag.retrieval.pipeline import DenseRerankPipeline, RetrievalConfig
from rag.retrieval.reranker import LexicalReranker


def test_reranker_promotes_query_term_overlap() -> None:
    candidates = [
        SearchResult("unrelated database text", {"chunk_hash": "a"}, 0.9, "hybrid"),
        SearchResult("Lambda timeout uses CloudWatch Logs", {"chunk_hash": "b"}, 0.5, "hybrid"),
    ]
    results = asyncio.run(LexicalReranker().rerank("Lambda timeout", candidates, limit=2))
    assert results[0].chunk_hash == "b"
    assert results[0].rerank_rank == 1
    assert results[0].rerank_score is not None


class StubRetriever:
    async def retrieve(
        self,
        query: str,
        *,
        limit: int = 10,
        filters: dict[str, MetadataValue] | None = None,
    ) -> list[SearchResult]:
        return [
            SearchResult(
                "first",
                {"chunk_hash": "first", "chunk_id": "first"},
                0.9,
                "dense",
                retrieval_rank=1,
                retrieval_score=0.9,
            ),
            SearchResult(
                "second",
                {"chunk_hash": "second", "chunk_id": "second"},
                0.8,
                "dense",
                retrieval_rank=2,
                retrieval_score=0.8,
            ),
        ]


class TimeoutReranker:
    async def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        *,
        limit: int,
    ) -> list[SearchResult]:
        raise TimeoutError("simulated timeout")


def test_reranker_fallback() -> None:
    config = RetrievalConfig(
        mode="dense",
        candidate_k=2,
        rerank_k=2,
        final_k=2,
        reranker_timeout_seconds=0.01,
    )
    pipeline = DenseRerankPipeline(
        dense=StubRetriever(),
        reranker=TimeoutReranker(),
        config=config,
    )
    outcome = asyncio.run(pipeline.retrieve("query"))
    assert [item.chunk_id for item in outcome.results] == ["first", "second"]
    assert outcome.diagnostics.reranker_fallback is True
    assert outcome.diagnostics.reranked_candidates == 0
