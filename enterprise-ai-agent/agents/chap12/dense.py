"""Sample-scoped dense retrieval reusing the Project 1 MiniLM vectors.

The full semantic index (801,996 documents) cannot be queried directly: its hits fall
outside the sample. Instead, the already-computed chunk vectors of the sample documents are
copied into a sidecar file, and queries are encoded with the same pinned MiniLM encoder, so
document vectors are byte-identical to Project 1 and nothing is re-embedded.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from rag.retrieval.contracts import SearchResult
from rag.retrieval.filters import FilterPolicy, metadata_matches

DIMENSION = 384


def build_sidecar(semantic_dir: Path, sample_index: Path, destination: Path) -> dict[str, Any]:
    if destination.exists():
        raise FileExistsError(f"{destination} exists; dense sidecars are immutable")
    manifest = json.loads((semantic_dir / "manifest.json").read_text(encoding="utf-8"))
    if not manifest.get("complete") or manifest.get("dimension") != DIMENSION:
        raise ValueError("full semantic index is incomplete or has another dimension")
    sample = sqlite3.connect(sample_index.resolve().as_uri() + "?mode=ro", uri=True)
    source = sqlite3.connect((semantic_dir / "chunks.sqlite").resolve().as_uri() + "?mode=ro",
                             uri=True)
    output = sqlite3.connect(destination)
    try:
        output.execute("PRAGMA journal_mode=MEMORY")
        output.executescript("""
            CREATE TABLE chunks (rowid INTEGER PRIMARY KEY, chunk_id TEXT UNIQUE,
                doc_id TEXT NOT NULL, text TEXT NOT NULL, metadata TEXT NOT NULL,
                vector BLOB NOT NULL);
            CREATE TABLE manifest (key TEXT PRIMARY KEY, value TEXT);
        """)
        doc_ids = [r[0] for r in sample.execute("SELECT doc_id FROM docs ORDER BY doc_id")]
        missing = 0
        for doc_id in doc_ids:
            rows = source.execute("SELECT chunk_id, doc_id, text, metadata, vector FROM chunks "
                                  "WHERE doc_id=? ORDER BY rowid", (doc_id,)).fetchall()
            missing += not rows
            output.executemany("INSERT INTO chunks(chunk_id,doc_id,text,metadata,vector) "
                               "VALUES (?,?,?,?,?)", rows)
        chunks = output.execute("SELECT count(*) FROM chunks").fetchone()[0]
        sample_manifest = dict(sample.execute("SELECT key, value FROM manifest"))
        info = {"embedding_id": manifest["embedding_id"], "encoder": json.dumps(
            manifest["encoder"], sort_keys=True), "documents": str(len(doc_ids) - missing),
            "documents_missing": str(missing), "chunks": str(chunks),
            "sample_scope": sample_manifest["scope"],
            "sample_seed": sample_manifest.get("seed", ""),
            "complete": "true"}
        output.executemany("INSERT INTO manifest VALUES (?,?)", info.items())
        output.commit()
        return info
    finally:
        sample.close()
        source.close()
        output.close()


class SampleDenseRetriever:
    """Exact cosine search over the sample's MiniLM chunk vectors (unit vectors, inner product)."""

    def __init__(self, sidecar: Path, encoder: Any | None = None) -> None:
        import numpy as np

        with closing(sqlite3.connect(sidecar.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            self.manifest = dict(db.execute("SELECT key, value FROM manifest"))
            rows = db.execute("SELECT text, metadata, vector FROM chunks ORDER BY rowid").fetchall()
        if self.manifest.get("complete") != "true":
            raise ValueError("dense sidecar is incomplete")
        self.texts = [r[0] for r in rows]
        self.metadata = [json.loads(r[1]) for r in rows]
        self.vectors = np.frombuffer(b"".join(r[2] for r in rows), dtype="float32").reshape(
            len(rows), DIMENSION)
        if encoder is None:
            from rag.techqa.semantic import MiniLMEncoder

            encoder = MiniLMEncoder(batch_size=32, device="cpu")
            if encoder.identity != self.manifest["embedding_id"]:
                raise ValueError("query encoder differs from the encoder of the stored vectors")
        self.encoder = encoder
        self.policy = FilterPolicy()
        self._chunk_rows = {str(m.get("chunk_id")): i for i, m in enumerate(self.metadata)}

    def by_chunk_index(self, chunk_id: str) -> int | None:
        return self._chunk_rows.get(chunk_id)

    async def retrieve(self, query: str, *, limit: int = 30,
                       filters: dict[str, Any] | None = None) -> list[SearchResult]:
        import asyncio

        import numpy as np

        secure = self.policy.apply(filters)
        vector = (await asyncio.to_thread(self.encoder.encode, [query]))[0]
        scores = self.vectors @ vector
        order = np.argsort(-scores, kind="stable")
        output: list[SearchResult] = []
        for index in order:
            meta = self.metadata[int(index)]
            if not metadata_matches(meta, secure):
                continue
            rank = len(output) + 1
            score = float(scores[int(index)])
            output.append(SearchResult(
                text=self.texts[int(index)], metadata=meta, score=score, backend="dense",
                retrieval_rank=rank, retrieval_score=score, dense_rank=rank,
                retrieval_sources=("dense",)))
            if len(output) == limit:
                break
        return output


class VectorReranker:
    """Project 1 rerank formula with MiniLM cosine as the semantic term.

    score = w_sem * cos(query, chunk) + w_lex * term coverage + w_prior * BM25 rank prior,
    i.e. TechQAReranker's formula; only the semantic model differs (stored MiniLM chunk
    vectors instead of nomic embeddings fetched from Ollama), so it also works offline.
    """

    def __init__(self, dense: SampleDenseRetriever, weights: tuple[float, float, float] = (
            0.5, 0.3, 0.2)) -> None:
        self.dense, self.weights = dense, weights

    async def rerank(self, query: str, candidates: list[SearchResult], *,
                     limit: int = 20) -> list[SearchResult]:
        import asyncio
        from dataclasses import replace

        from rag.techqa.retrieval import coverage

        if not candidates or limit <= 0:
            return []
        vector = (await asyncio.to_thread(self.dense.encoder.encode, [query]))[0]
        semantic_w, lexical_w, prior_w = self.weights
        ranked = []
        for candidate in candidates:
            row = self.dense.by_chunk_index(candidate.chunk_id)
            semantic = float(self.dense.vectors[row] @ vector) if row is not None else 0.0
            title = str(candidate.metadata.get("context_summary", ""))
            lexical = coverage(query, title + " " + candidate.text)
            prior = 1 / (1 + int(candidate.metadata.get("bm25_document_rank", 1000)) / 5)
            score = semantic_w * semantic + lexical_w * lexical + prior_w * prior
            ranked.append(replace(candidate, score=score, rerank_score=score,
                                  backend=candidate.backend + "+minilm_rerank"))
        ranked.sort(key=lambda result: result.score, reverse=True)
        return [replace(r, rerank_rank=rank) for rank, r in enumerate(ranked[:limit], 1)]
