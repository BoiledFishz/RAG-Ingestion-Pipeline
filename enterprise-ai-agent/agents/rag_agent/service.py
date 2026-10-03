"""Bounded agent: rewrite/clarify -> tool -> compress -> select -> validate."""

from __future__ import annotations

import logging
import time

from pydantic import ValidationError

from agents.rag_agent.compression import ContextCompressor
from agents.rag_agent.generation import EvidenceSelector, grounded_response
from agents.rag_agent.rewrite import QueryRewriter
from models.errors import InvalidEvidence
from models.schemas import AgentResponse, AgentRun, QueryRequest, RetrieverInput, RunTrace
from tools.retriever import RetrieverTool

LOGGER = logging.getLogger(__name__)
REFUSAL = "知识库无法回答该问题。"


class RAGAgent:
    def __init__(
        self,
        rewriter: QueryRewriter,
        retriever: RetrieverTool,
        compressor: ContextCompressor,
        selector: EvidenceSelector,
        top_k: int = 8,
    ) -> None:
        if not 1 <= top_k <= 30:
            raise ValueError("top_k must be between 1 and 30")
        self.rewriter, self.retriever = rewriter, retriever
        self.compressor, self.selector, self.top_k = compressor, selector, top_k

    async def run(self, request: QueryRequest) -> AgentRun:
        started = time.perf_counter()
        # Validate filters even if the question is ambiguous.
        self.retriever.secure_filters(request.filters)
        trace = RunTrace(original_query=request.query)
        rewritten = await self.rewriter.rewrite(request.query)
        trace.rewritten_query, trace.rewrite_fallback = rewritten.query, rewritten.fallback

        def finish(response: AgentResponse) -> AgentRun:
            trace.latency_ms = (time.perf_counter() - started) * 1000
            LOGGER.info(
                "Agent status=%s candidates=%d context_tokens=%d latency_ms=%.2f",
                trace.status,
                len(trace.candidate_ids),
                trace.context_tokens,
                trace.latency_ms,
            )
            return AgentRun(response=response, trace=trace)

        if rewritten.action == "clarify":
            trace.status = "clarified"
            return finish(AgentResponse(answer=rewritten.clarification, sources=[], confidence=0))

        trace.tool_called = True
        candidates = await self.retriever.invoke(
            RetrieverInput(
                query=rewritten.query,
                top_k=self.top_k,
                filters=request.filters,
            )
        )
        trace.candidate_ids = [d.chunk_id for d in candidates]
        compressed = self.compressor.compress(rewritten.query, candidates)
        trace.evidence = compressed.evidence
        trace.original_tokens = compressed.original_tokens
        trace.context_tokens = compressed.context_tokens
        refusal = AgentResponse(answer=REFUSAL, sources=[], confidence=0)
        if not compressed.evidence:
            return finish(refusal)

        correction = ""
        for attempt in range(2):
            try:
                draft = await self.selector.select(
                    request.query,
                    compressed.evidence,
                    correction=correction,
                )
                if not draft.quotes:
                    return finish(refusal)
                response = grounded_response(draft, compressed.evidence)
                trace.status = "answered"
                return finish(response)
            except (InvalidEvidence, ValidationError) as exc:
                detail = str(exc)[:800]
                trace.validation_failures.append(detail)
                LOGGER.warning(
                    "Invalid structured evidence, attempt=%d: %s",
                    attempt + 1,
                    detail,
                )
                trace.retries = min(attempt + 1, 1)
                correction = (
                    "Your previous output failed validation. Return only sufficient and "
                    "source_ids from the allowed IDs; use sufficient=false and source_ids=[] "
                    "when unsupported. Do not return quotes or excerpt text. "
                    "For the applicability audit, conflict claims MUST be exact short "
                    "substrings of QUESTION and the supplied source, not its unseen parent. "
                    "Fix-release information is not a conflicting migration direction."
                    f"\nVALIDATION ERROR (diagnostic data): {detail}"
                    "\nAllowed source IDs: "
                    + ", ".join(item.source_id for item in compressed.evidence)
                )
        trace.status = "invalid_evidence"
        return finish(refusal)
