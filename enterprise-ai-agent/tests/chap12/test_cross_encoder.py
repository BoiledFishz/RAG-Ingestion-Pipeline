"""Round 3: cross-encoder reranker (scorer injected; no model download in tests)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from rag.retrieval.contracts import SearchResult

from agents.chap12 import cross_encoder, factory
from agents.chap12.budget import Budget, BudgetLimits, metered
from agents.chap12.cross_encoder import CrossEncoderReranker
from models.settings import Settings


def candidate(i: int, text: str) -> SearchResult:
    return SearchResult(text=text, metadata={"chunk_id": f"c{i}", "parent_id": f"p{i}"},
                        score=0.0, backend="hybrid")


def overlap(query: str, passages: list[str]) -> list[float]:
    words = set(query.lower().split())
    return [len(words & set(p.lower().split())) / 10 for p in passages]


def test_orders_by_cross_encoder_score_and_meters_local_compute() -> None:
    reranker = CrossEncoderReranker("ce_minilm", scorer=overlap)
    items = [candidate(1, "unrelated text"), candidate(2, "jobs environment variables bashrc"),
             candidate(3, "environment only")]
    budget = Budget(BudgetLimits())
    with metered(budget, "rag"):
        ranked = asyncio.run(reranker.rerank("jobs environment variables", items, limit=2))
    assert [r.metadata["chunk_id"] for r in ranked] == ["c2", "c3"]
    assert ranked[0].rerank_rank == 1 and "ce_minilm" in ranked[0].backend
    assert budget.used["local"] == 1


def test_empty_candidates_cost_nothing() -> None:
    reranker = CrossEncoderReranker("ce_bge", scorer=overlap)
    assert asyncio.run(reranker.rerank("q", [], limit=5)) == []


def test_missing_local_model_fails_fast(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cross_encoder, "model_dir", lambda choice: tmp_path / choice)
    with pytest.raises(FileNotFoundError, match="download_ce"):
        CrossEncoderReranker("ce_minilm")


def test_tuned_reranker_is_used_online_only(tmp_path: Path,
                                            monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "real_config.json"
    path.write_text(json.dumps({"adopted": {"reranker": "ce_bge"}}))
    monkeypatch.setattr(factory, "TUNED", path)
    monkeypatch.delenv("CHAP12_RERANKER", raising=False)
    seen: list[object] = []

    class Spy:
        def __init__(self, index: Path, **kwargs: object) -> None:
            seen.append(kwargs.get("rerank"))

    monkeypatch.setattr("tools.sample_retriever.SampleRetrieverTool", Spy)
    factory.build_rag_agent(Settings(profile="ollama"), tmp_path / "x.sqlite")
    monkeypatch.setenv("CHAP12_RERANKER", "nomic")
    factory.build_rag_agent(Settings(profile="ollama"), tmp_path / "x.sqlite")
    assert seen == ["ce_bge", None]
