"""P2: fine-grained budget categories (sql, local, embedding misses vs cache hits)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from rag.retrieval.contracts import SearchResult

from agents.chap12.budget import Budget, BudgetedEmbedder, BudgetExhausted, BudgetLimits, metered
from agents.chap12.contracts import AnalysisRequest
from agents.chap12.factory import build_supervisor
from agents.chap12.metered import CountingReranker, MeteredIndex
from models.settings import Settings
from tests.chap12.conftest import AGENT_ROOT, context


def test_every_sql_statement_is_counted_per_worker(sample_index: Path,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TECHQA_PROFILE", "fixture")
    sup = build_supervisor(Settings(profile="offline"), sample_index)
    result = asyncio.run(sup.run(AnalysisRequest(
        query="Streams jobs do not inherit environment variables from .bashrc"), context()))
    rag, db = result.worker_results
    assert rag.usage.sql_statements > 0 and db.usage.sql_statements > 0
    assert result.usage.sql_statements == rag.usage.sql_statements + db.usage.sql_statements


def test_sql_cap_blocks_the_next_statement(sample_index: Path) -> None:
    index = MeteredIndex(sample_index)
    budget = Budget(BudgetLimits(max_sql_statements=1))

    def search() -> None:
        with metered(budget, "rag"):
            index.search("streams environment variables bashrc", 5)

    with pytest.raises(BudgetExhausted) as info:
        search()
    assert info.value.kind == "sql" and budget.used["sql"] == 1


class FakeEmbedder:
    model = "fake"

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t)), 1.0] for t in texts]


def test_embedding_misses_and_cache_hits_are_separate(monkeypatch: pytest.MonkeyPatch) -> None:
    reranker = CountingReranker(True)
    reranker.embedder = BudgetedEmbedder(FakeEmbedder())  # type: ignore[assignment]
    reranker.cache = AGENT_ROOT / ".test_tmp" / f"cache-{uuid4().hex}.sqlite"
    reranker.cache.parent.mkdir(parents=True, exist_ok=True)
    candidates = [SearchResult(text=f"document {i} about streams", metadata={
        "chunk_id": f"c{i}", "context_summary": "t"}, score=0.0, backend="sparse")
                  for i in range(3)]
    budget = Budget(BudgetLimits())

    async def rerank() -> None:
        with metered(budget, "rag"):
            await reranker.rerank("streams", candidates)

    asyncio.run(rerank())
    assert budget.used["embedding"] == 1 and budget.embedding_cache_hits == 0
    asyncio.run(rerank())
    assert budget.used["embedding"] == 1 and budget.embedding_cache_hits == 4  # query + 3
