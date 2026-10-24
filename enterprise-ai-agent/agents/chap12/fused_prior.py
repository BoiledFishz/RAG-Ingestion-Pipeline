"""Round 10 (2026-10-24): rerank prior from the fused (RRF) rank instead of the BM25 rank.

The Project 1 reranker scores 0.5 semantic + 0.3 lexical + 0.2 * 1 / (1 + BM25_rank / 5), and a
candidate that only the dense retriever found gets BM25 rank 1000 (prior about 0.005). The
offline study (results/chap12/recall_rerank_study.json) found 13 of the 22 gold documents pushed
out of the top 8 were such dense-only hits, usually with a higher semantic score than the 8th
document. This subclass hands the Project 1 reranker each candidate's position in the fused list
as its rank, so the prior rewards documents that either retriever ranked well. Semantic and
lexical scores, weights, caching and metering are unchanged; Project 1 is not modified.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from rag.retrieval.contracts import SearchResult

from agents.chap12.metered import CountingReranker


class FusedPriorReranker(CountingReranker):
    async def rerank(self, query: str, candidates: list[SearchResult], *, limit: int = 20,
                     components: dict[str, dict[str, float]] | None = None
                     ) -> list[SearchResult]:
        # Candidates arrive in fused (RRF) order from the pipeline; rank = position.
        ranked: list[Any] = [replace(c, metadata={**c.metadata, "bm25_document_rank": i})
                             for i, c in enumerate(candidates, 1)]
        result: list[SearchResult] = await super().rerank(query, ranked, limit=limit,
                                                          components=components)
        return result
