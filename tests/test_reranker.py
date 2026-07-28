from __future__ import annotations

import asyncio

from rag.retrieval.contracts import SearchResult
from rag.retrieval.reranker import LexicalReranker


def test_reranker_promotes_query_term_overlap() -> None:
    candidates = [
        SearchResult("unrelated database text", {"chunk_hash": "a"}, 0.9, "hybrid"),
        SearchResult("Lambda timeout uses CloudWatch Logs", {"chunk_hash": "b"}, 0.5, "hybrid"),
    ]
    results = asyncio.run(LexicalReranker().rerank("Lambda timeout", candidates, limit=2))
    assert results[0].chunk_hash == "b"
