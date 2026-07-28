from __future__ import annotations

import asyncio

from rag.generation.service import RAGService
from rag.ingestion.models import MetadataValue
from rag.retrieval.context_builder import ContextBuilder
from rag.retrieval.contracts import (
    RetrievalDiagnostics,
    RetrievalMode,
    RetrievalOutcome,
    SearchResult,
)


class StubEngine:
    def __init__(self, results: list[SearchResult]) -> None:
        self.results = results

    async def retrieve(
        self,
        query: str,
        *,
        mode: RetrievalMode = "dense",
        filters: dict[str, MetadataValue] | None = None,
    ) -> RetrievalOutcome:
        return RetrievalOutcome(
            results=self.results,
            diagnostics=RetrievalDiagnostics(
                mode=mode,
                dense_candidates=len(self.results),
                final_chunks=len(self.results),
            ),
        )


class SequenceGenerator:
    def __init__(self, answers: list[str]) -> None:
        self.answers = answers
        self.calls = 0

    async def generate(
        self,
        *,
        question: str,
        context: str,
        correction: str | None = None,
    ) -> str:
        answer = self.answers[min(self.calls, len(self.answers) - 1)]
        self.calls += 1
        return answer


def _result() -> SearchResult:
    return SearchResult(
        text="An explicit deny overrides an allow.",
        metadata={
            "chunk_id": "chunk-1",
            "chunk_hash": "hash-1",
            "source_file": "iam.pdf",
            "page_number": 3,
            "status": "published",
        },
        score=0.9,
        backend="dense",
        retrieval_rank=1,
        retrieval_score=0.9,
    )


def test_invalid_citation_rejected() -> None:
    generator = SequenceGenerator(["Incorrect citation [S7].", "Still incorrect [S7]."])
    service = RAGService(
        retriever=StubEngine([_result()]),
        generator=generator,
        context_builder=ContextBuilder(max_context_tokens=200),
    )
    response = asyncio.run(service.query("What overrides an allow?"))
    assert response.refused is True
    assert response.refusal_reason == "invalid_citation"
    assert response.citations == []
    assert generator.calls == 2


def test_no_results_skips_llm() -> None:
    generator = SequenceGenerator(["should not be used"])
    service = RAGService(retriever=StubEngine([]), generator=generator)
    response = asyncio.run(service.query("unknown"))
    assert response.refused is True
    assert response.refusal_reason == "no_retrieval_results"
    assert generator.calls == 0
