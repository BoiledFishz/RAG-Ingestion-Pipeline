"""Round 10: rerank prior from the fused rank; candidate_k setting."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from rag.retrieval.contracts import SearchResult

from agents.chap12.fused_prior import FusedPriorReranker
from agents.chap12.metered import CountingReranker


def cand(i: int, bm25_rank: int | None) -> SearchResult:
    meta = {"chunk_id": f"c{i}", "parent_id": f"p{i}", "context_summary": "jobs env"}
    if bm25_rank is not None:
        meta["bm25_document_rank"] = bm25_rank
    return SearchResult(text="jobs environment variables", metadata=meta, score=0.0,
                        backend="hybrid")


def order(reranker: CountingReranker) -> list[str]:
    items = [cand(1, None), cand(2, 1)]  # fused order: a dense-only hit first
    ranked = asyncio.run(reranker.rerank("jobs environment variables", items, limit=2))
    return [r.metadata["chunk_id"] for r in ranked]


def test_dense_only_hit_is_no_longer_scored_as_bm25_rank_1000() -> None:
    assert order(CountingReranker(False)) == ["c2", "c1"]  # Project 1 prior: c1 rank 1000
    assert order(FusedPriorReranker(False)) == ["c1", "c2"]  # fused rank 1 beats rank 2


def test_retriever_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tools import sample_retriever

    for name in ("MeteredIndex", "DocumentScope", "TechQAParentResolver", "FullSparseRetriever"):
        monkeypatch.setattr(sample_retriever, name, lambda *a, **k: object())
    monkeypatch.delenv("CHAP12_RERANK_PRIOR", raising=False)
    monkeypatch.delenv("CHAP12_CANDIDATE_K", raising=False)
    default = sample_retriever.SampleRetrieverTool(tmp_path / "x.sqlite", rerank="nomic",
                                                   use_dense=False)
    assert type(default.pipeline.reranker) is CountingReranker
    assert default.pipeline.config.candidate_k == 30
    tuned = sample_retriever.SampleRetrieverTool(tmp_path / "x.sqlite", rerank="nomic",
                                                 use_dense=False, rerank_prior="fused",
                                                 candidate_k=50)
    assert type(tuned.pipeline.reranker) is FusedPriorReranker
    assert tuned.pipeline.config.candidate_k == 50
    monkeypatch.setenv("CHAP12_RERANK_PRIOR", "bm25")
    monkeypatch.setenv("CHAP12_CANDIDATE_K", "30")
    forced = sample_retriever.SampleRetrieverTool(tmp_path / "x.sqlite", rerank="nomic",
                                                  use_dense=False, rerank_prior="fused",
                                                  candidate_k=50)
    assert type(forced.pipeline.reranker) is CountingReranker
    assert forced.pipeline.config.candidate_k == 30
