"""Grounded RAG orchestration with refusal and citation controls."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, replace
from typing import Any

from rag.generation.generator import AnswerGenerator
from rag.ingestion.models import MetadataValue
from rag.retrieval.context_builder import Citation, CitationValidator, ContextBuilder
from rag.retrieval.contracts import (
    ParentResolver,
    RetrievalDiagnostics,
    RetrievalEngine,
    RetrievalMode,
)

LOGGER = logging.getLogger(__name__)
REFUSAL_ANSWER = "知识库无法回答该问题。"


@dataclass(frozen=True, slots=True)
class RAGResponse:
    answer: str
    citations: list[Citation]
    retrieval: dict[str, Any]
    refused: bool
    refusal_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "citations": [asdict(citation) for citation in self.citations],
            "retrieval": self.retrieval,
            "refused": self.refused,
            "refusal_reason": self.refusal_reason,
        }


class RAGService:
    def __init__(
        self,
        *,
        retriever: RetrievalEngine,
        generator: AnswerGenerator,
        context_builder: ContextBuilder | None = None,
        citation_validator: CitationValidator | None = None,
        parent_resolver: ParentResolver | None = None,
        relevance_threshold: float = 0.0,
        relevance_thresholds: dict[RetrievalMode, float] | None = None,
    ) -> None:
        self.retriever = retriever
        self.generator = generator
        self.context_builder = context_builder or ContextBuilder()
        self.citation_validator = citation_validator or CitationValidator()
        self.parent_resolver = parent_resolver
        self.relevance_threshold = relevance_threshold
        self.relevance_thresholds = relevance_thresholds or {}

    async def query(
        self,
        query: str,
        *,
        mode: RetrievalMode = "dense",
        filters: dict[str, MetadataValue] | None = None,
    ) -> RAGResponse:
        outcome = await self.retriever.retrieve(query, mode=mode, filters=filters)
        if not outcome.results:
            return self._refusal(outcome.diagnostics, "no_retrieval_results")

        threshold = self.relevance_thresholds.get(mode, self.relevance_threshold)
        relevant = [
            result
            for result in outcome.results
            if (result.rerank_score if result.rerank_score is not None else result.score)
            >= threshold
        ]
        if not relevant:
            return self._refusal(outcome.diagnostics, "below_relevance_threshold")

        built = await self.context_builder.build_with_parents(
            relevant,
            parent_resolver=self.parent_resolver,
        )
        diagnostics = replace(
            outcome.diagnostics,
            final_chunks=len(built.selected_results),
            context_tokens=built.token_count,
        )
        if not built.context or not built.selected_results:
            return self._refusal(diagnostics, "empty_context")

        answer = await self.generator.generate(question=query, context=built.context)
        validation = self.citation_validator.validate(answer, built.source_map)
        if not validation.valid:
            LOGGER.warning(
                "Invalid citations %s; retrying generation once",
                validation.invalid_source_ids,
            )
            allowed = ", ".join(f"[{key}]" for key in built.source_map)
            answer = await self.generator.generate(
                question=query,
                context=built.context,
                correction=(
                    "Your previous answer used missing or invalid citations. "
                    f"Rewrite it once using only these source IDs: {allowed}."
                ),
            )
            validation = self.citation_validator.validate(answer, built.source_map)
            if not validation.valid:
                LOGGER.warning(
                    "Citation repair failed with invalid IDs %s",
                    validation.invalid_source_ids,
                )
                return self._refusal(diagnostics, "invalid_citation")

        citations = [
            built.source_map[source_id]
            for source_id in validation.referenced_source_ids
            if source_id in built.source_map
        ]
        return RAGResponse(
            answer=answer,
            citations=citations,
            retrieval=asdict(diagnostics),
            refused=False,
        )

    @staticmethod
    def _refusal(diagnostics: RetrievalDiagnostics, reason: str) -> RAGResponse:
        return RAGResponse(
            answer=REFUSAL_ANSWER,
            citations=[],
            retrieval=asdict(diagnostics),
            refused=True,
            refusal_reason=reason,
        )
