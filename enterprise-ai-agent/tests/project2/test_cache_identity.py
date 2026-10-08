"""Existing cache identity must bind real text, versions and trusted scope."""

import asyncio
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from agents.project2.batched_retrieval import BatchedReranker
from agents.project2.cache_identity import authorization_scope, cache_context, embedding_key
from agents.project2.policy import TrustedContext

ROOT = Path(__file__).resolve().parents[3]


def official_text() -> str:
    with sqlite3.connect(
        (ROOT / ".rag_data/techqa_full.sqlite").resolve().as_uri() + "?mode=ro", uri=True
    ) as db:
        return db.execute("SELECT text FROM docs ORDER BY doc_id LIMIT 1").fetchone()[0]


def owner(tenant: str = "local", subject: str = "owner") -> TrustedContext:
    return TrustedContext(subject, tenant, frozenset({"full"}), frozenset({"rag_explain"}))


def test_cache_key_changes_with_model_text_data_and_authorization() -> None:
    text = official_text()
    scope = authorization_scope(owner())
    key = embedding_key("nomic-embed-text", text, "index-v1", scope)
    assert key != embedding_key("other-model", text, "index-v1", scope)
    assert key != embedding_key("nomic-embed-text", text[:-1], "index-v1", scope)
    assert key != embedding_key("nomic-embed-text", text, "index-v2", scope)
    assert key != embedding_key(
        "nomic-embed-text", text, "index-v1", authorization_scope(owner("other"))
    )
    assert key != embedding_key(
        "nomic-embed-text", text, "index-v1", authorization_scope(owner(subject="other"))
    )
    with pytest.raises(PermissionError):
        authorization_scope(TrustedContext("owner", "local", frozenset({"full"}), frozenset()))


def test_rerank_cache_cannot_reuse_across_tenants_or_data_versions(tmp_path: Path) -> None:
    calls = []

    async def embed(texts):
        calls.append(texts)
        return [[1.0, 0.0] for _ in texts]  # Adapter contract Mock, official text only.

    reranker = BatchedReranker(False)
    reranker.embedder = SimpleNamespace(model="nomic-embed-text", embed_documents=embed)
    reranker.cache = tmp_path / "cache.sqlite"
    text = official_text()
    with cache_context("index-v1", authorization_scope(owner())):
        assert asyncio.run(reranker.embeddings([text])) == [[1.0, 0.0]]
        assert asyncio.run(reranker.embeddings([text])) == [[1.0, 0.0]]
    assert len(calls) == 1
    with cache_context("index-v1", authorization_scope(owner("other"))):
        asyncio.run(reranker.embeddings([text]))
    with cache_context("index-v2", authorization_scope(owner())):
        asyncio.run(reranker.embeddings([text]))
    assert len(calls) == 3
