from __future__ import annotations

import asyncio

from rag.generation.service import RAGService
from rag.ingestion.models import MetadataValue
from rag.retrieval.contracts import SearchResult
from rag.retrieval.pipeline import RetrievalPipeline
from rag.techqa.data import questions


class Retriever:
    async def retrieve(
        self, query: str, *, limit: int = 10,
        filters: dict[str, MetadataValue] | None = None,
    ) -> list[SearchResult]:
        assert filters == {"status": "published"}
        return [SearchResult(
            text=questions("fixture")[0]["ANSWER"],
            metadata={"chunk_id": "streams", "source_file": "swg21996508.md", "page_number": 1},
            score=0.4, backend="dense", retrieval_rank=1,
        )]


class FailingReranker:
    async def rerank(
        self, query: str, candidates: list[SearchResult], *, limit: int,
    ) -> list[SearchResult]:
        raise TimeoutError("model unavailable")


class Generator:
    calls = 0

    async def generate(
        self, *, question: str, context: str, correction: str | None = None,
    ) -> str:
        self.calls += 1
        return questions("fixture")[0]["ANSWER"] + " [S1]."


def test_fallback_survives_rrf_score_scale_but_still_refuses_unrelated_query() -> None:
    async def scenario() -> None:
        generator = Generator()
        service = RAGService(
            retriever=RetrievalPipeline(
                dense=Retriever(), sparse=Retriever(), reranker=FailingReranker(),
            ),
            generator=generator,
            relevance_thresholds={"hybrid": 0.545},
        )
        response = await service.query(
            "streamtool setproperty environment variables", mode="hybrid"
        )
        assert not response.refused
        assert response.retrieval["reranker_fallback"]
        assert response.citations[0].chunk_id == "streams"
        refused = await service.query("Mars weather forecast tomorrow", mode="hybrid")
        assert refused.refused
        assert generator.calls == 1

    asyncio.run(scenario())
