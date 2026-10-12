"""Sample dense sidecar, MiniLM-style rerank and hybrid retrieval with a deterministic encoder."""

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from rag.techqa.retrieval import legacy_chunks

from agents.chap12.dense import SampleDenseRetriever, VectorReranker, build_sidecar
from models.schemas import RetrieverInput
from tests.chap12.conftest import AGENT_ROOT, fixture_docs
from tools.sample_retriever import SampleRetrieverTool


class HashEncoder:
    """Deterministic bag-of-words unit vectors; stands in for MiniLM in tests only."""

    identity = "test-encoder"

    def encode(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), 384), dtype="float32")
        for row, text in enumerate(texts):
            for word in text.lower().split():
                out[row, int(hashlib.sha256(word.encode()).hexdigest(), 16) % 384] += 1
        return out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-9)


@pytest.fixture(scope="module")
def own_index(sample_index: Path) -> Path:
    """Private copy: a sidecar next to the shared index would change other tests' wiring."""
    path = AGENT_ROOT / ".test_tmp" / f"chap12-dense-{uuid4().hex}" / "sample.sqlite"
    path.parent.mkdir(parents=True)
    shutil.copyfile(sample_index, path)
    return path


@pytest.fixture(scope="module")
def sidecar(own_index: Path) -> Path:
    sample_index = own_index
    semantic = AGENT_ROOT / ".test_tmp" / f"semantic-{uuid4().hex}"
    semantic.mkdir(parents=True)
    (semantic / "manifest.json").write_text(json.dumps({
        "complete": True, "dimension": 384, "embedding_id": "test-encoder",
        "encoder": {"model": "test"}}))
    db = sqlite3.connect(semantic / "chunks.sqlite")
    db.execute("CREATE TABLE chunks (rowid INTEGER PRIMARY KEY, chunk_id TEXT, doc_id TEXT, "
               "text TEXT, metadata TEXT, vector BLOB)")
    encoder = HashEncoder()
    for doc in fixture_docs():
        for chunk in legacy_chunks(doc):
            db.execute("INSERT INTO chunks(chunk_id,doc_id,text,metadata,vector) "
                       "VALUES (?,?,?,?,?)",
                       (chunk.chunk_id, doc["id"], chunk.text, json.dumps(chunk.metadata),
                        encoder.encode([chunk.text])[0].tobytes()))
    db.commit()
    db.close()
    destination = sample_index.with_suffix(".dense.sqlite")
    info = build_sidecar(semantic, sample_index, destination)
    assert info["documents_missing"] == "0" and int(info["chunks"]) > 41
    with pytest.raises(FileExistsError):
        build_sidecar(semantic, sample_index, destination)
    return destination


def test_dense_retrieval_ranks_matching_chunk_first(sidecar: Path) -> None:
    dense = SampleDenseRetriever(sidecar, encoder=HashEncoder())
    results = asyncio.run(dense.retrieve(
        "streams jobs environment variables bashrc system service", limit=5))
    assert results[0].metadata["techqa_document_id"] == "swg21996508"
    assert [r.dense_rank for r in results] == [1, 2, 3, 4, 5]


def test_vector_rerank_uses_project1_formula(sidecar: Path) -> None:
    dense = SampleDenseRetriever(sidecar, encoder=HashEncoder())
    query = "streams environment variables bashrc"
    candidates = asyncio.run(dense.retrieve(query, limit=6))
    ranked = asyncio.run(VectorReranker(dense, (1.0, 0.0, 0.0)).rerank(query, candidates))
    vector = HashEncoder().encode([query])[0]
    expected = sorted((float(dense.vectors[dense.by_chunk_index(c.chunk_id)] @ vector)
                       for c in candidates), reverse=True)
    assert [round(r.score, 6) for r in ranked] == [round(x, 6) for x in expected]


def test_hybrid_tool_uses_tune_threshold(sidecar: Path, own_index: Path,
                                         monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHAP12_MINILM_THRESHOLD", "0.0")
    dense = SampleDenseRetriever(sidecar, encoder=HashEncoder())
    tool = SampleRetrieverTool(own_index, dense=dense, rerank="minilm")
    assert tool.mode == "hybrid"
    docs = asyncio.run(tool.invoke(RetrieverInput(
        query="Streams 4.1.1.1 jobs do not inherit environment variables from .bashrc", top_k=5)))
    assert "techqa:swg21996508:parent" in [d.chunk_id for d in docs]
    assert {d.metadata["_acceptance_threshold"] for d in docs} == {0.0}


def test_gap_gate_refuses_by_rejecting_every_candidate(sidecar: Path, own_index: Path,
                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHAP12_MINILM_THRESHOLD", "0.0")
    dense = SampleDenseRetriever(sidecar, encoder=HashEncoder())
    tool = SampleRetrieverTool(own_index, dense=dense, rerank="minilm")
    query = "Streams 4.1.1.1 jobs do not inherit environment variables from .bashrc"
    monkeypatch.setenv("CHAP12_GAP_GATE", "10")  # impossible gap: must refuse
    refused = asyncio.run(tool.invoke(RetrieverInput(query=query, top_k=5)))
    assert refused and {d.metadata["_acceptance_threshold"] for d in refused} == {1e9}
    monkeypatch.setenv("CHAP12_GAP_GATE", "")  # gate disabled
    kept = asyncio.run(tool.invoke(RetrieverInput(query=query, top_k=5)))
    assert {d.metadata["_acceptance_threshold"] for d in kept} == {0.0}
