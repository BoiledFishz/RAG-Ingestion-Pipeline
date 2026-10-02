from __future__ import annotations

import asyncio

from rag.ingestion.models import MetadataValue
from rag.retrieval.contracts import SearchResult
from rag.retrieval.pipeline import DenseRerankPipeline, RetrievalConfig
from rag.retrieval.reranker import CrossEncoderReranker, LexicalReranker
from rag.techqa.data import questions


def test_reranker_promotes_query_term_overlap() -> None:
    candidates = [
        SearchResult(questions("fixture")[1]["ANSWER"], {"chunk_hash": "a"}, 0.9, "hybrid"),
        SearchResult(questions("fixture")[0]["ANSWER"], {"chunk_hash": "b"}, 0.5, "hybrid"),
    ]
    results = asyncio.run(LexicalReranker().rerank("streamtool setproperty", candidates, limit=2))
    assert results[0].chunk_hash == "b"
    assert results[0].rerank_rank == 1
    assert results[0].rerank_score is not None


class StubCrossEncoder:
    def __init__(self) -> None:
        self.pairs: list[tuple[str, str]] = []

    def predict(
        self,
        sentences: list[tuple[str, str]],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> list[float]:
        self.pairs = sentences
        assert batch_size == 8
        assert show_progress_bar is False
        return [0.1, 0.9]


def test_cross_encoder_uses_query_text_and_context_summary() -> None:
    model = StubCrossEncoder()
    candidates = [
        SearchResult(
            questions("fixture")[1]["ANSWER"],
            {"chunk_id": "a", "context_summary": questions("fixture")[1]["QUESTION_TITLE"]},
            0.9,
            "dense",
            retrieval_rank=1,
            retrieval_score=0.9,
        ),
        SearchResult(
            questions("fixture")[0]["ANSWER"],
            {"chunk_id": "b", "context_summary": questions("fixture")[0]["QUESTION_TITLE"]},
            0.5,
            "dense",
            retrieval_rank=2,
            retrieval_score=0.5,
        ),
    ]

    results = asyncio.run(
        CrossEncoderReranker(model=model, batch_size=8).rerank(
            questions("fixture")[0]["QUESTION_TITLE"],
            candidates,
            limit=2,
        )
    )

    assert model.pairs[0][0] == questions("fixture")[0]["QUESTION_TITLE"]
    assert questions("fixture")[1]["QUESTION_TITLE"] in model.pairs[0][1]
    assert questions("fixture")[1]["ANSWER"] in model.pairs[0][1]
    assert results[0].chunk_id == "b"
    assert results[0].retrieval_rank == 2
    assert results[0].retrieval_score == 0.5
    assert results[0].rerank_rank == 1
    assert results[0].rerank_score == 0.9


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


class ThirtyCandidateRetriever:
    async def retrieve(
        self,
        query: str,
        *,
        limit: int = 10,
        filters: dict[str, MetadataValue] | None = None,
    ) -> list[SearchResult]:
        return [
            SearchResult(
                f"candidate {index}",
                {"chunk_hash": f"hash-{index}", "chunk_id": f"chunk-{index}"},
                1.0 - index / 100,
                "dense",
                retrieval_rank=index + 1,
                retrieval_score=1.0 - index / 100,
            )
            for index in range(limit)
        ]


class CapturingReranker:
    def __init__(self) -> None:
        self.received_count = 0
        self.requested_limit = 0

    async def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        *,
        limit: int,
    ) -> list[SearchResult]:
        self.received_count = len(candidates)
        self.requested_limit = limit
        return candidates[:limit]


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


def test_reranker_receives_top_30_and_returns_top_20_before_final_5() -> None:
    reranker = CapturingReranker()
    pipeline = DenseRerankPipeline(
        dense=ThirtyCandidateRetriever(),
        reranker=reranker,
        config=RetrievalConfig(
            mode="dense",
            candidate_k=30,
            rerank_k=20,
            final_k=5,
        ),
    )

    outcome = asyncio.run(pipeline.retrieve("query"))

    assert reranker.received_count == 30
    assert reranker.requested_limit == 20
    assert outcome.diagnostics.dense_candidates == 30
    assert outcome.diagnostics.reranked_candidates == 20
    assert len(outcome.results) == 5
