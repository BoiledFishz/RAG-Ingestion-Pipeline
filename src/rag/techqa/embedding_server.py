"""Local semantic search service, independent of the Docker database lifecycle."""

# mypy: disable-error-code="misc,untyped-decorator"

from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import closing
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag.retrieval.filters import FilterPolicy
from rag.techqa.semantic import SEMANTIC_ROOT, MiniLMEncoder, read_manifest

LOGGER = logging.getLogger(__name__)
app = FastAPI(title="TechQA semantic dense search")
INITIALIZATION_LOCK = Lock()


def metadata_connection(path: Path) -> sqlite3.Connection:
    """Never create or alter a database when serving an incomplete artifact."""
    return sqlite3.connect((path / "chunks.sqlite").resolve().as_uri() + "?mode=ro", uri=True)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20000)
    limit: int = Field(default=30, ge=1, le=100)
    filters: dict[str, str | int | float | bool] = Field(default_factory=dict)


class SemanticSearch:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.manifest = read_manifest(path)
        import faiss

        self.encoder = MiniLMEncoder(batch_size=32, device=os.getenv("TECHQA_QUERY_DEVICE", "cpu"))
        if self.encoder.identity != self.manifest["embedding_id"]:
            raise ValueError("Query/document semantic encoder identity mismatch")
        faiss.omp_set_num_threads(4)
        self.index = faiss.read_index(str(path / "index.faiss"))
        if self.index.ntotal != self.manifest["chunks"]:
            raise ValueError("Semantic manifest point count mismatch")
        with closing(metadata_connection(path)) as db:
            count = db.execute("SELECT count(*) FROM chunks").fetchone()[0]
            highest = db.execute("SELECT max(rowid) FROM chunks").fetchone()[0]
        if count != self.index.ntotal or highest != count:
            raise ValueError("Semantic metadata/vector coverage mismatch")
        LOGGER.info("Serving %s", self.manifest)

    def search(self, request: SearchRequest) -> list[dict[str, Any]]:
        import faiss
        import numpy as np

        faiss.omp_set_num_threads(4)
        filters = FilterPolicy().apply(request.filters)
        if any(filters.get(k, v) != v for k, v in {
            "status": "published", "language": "en", "document_type": "ibm_technote",
        }.items()):
            return []
        vector = self.encoder.encode([request.query])
        with closing(metadata_connection(self.path)) as db:
            source = filters.get("source_file")
            if source is not None:
                rows = db.execute(
                    "SELECT text,metadata,vector FROM chunks WHERE doc_id=?",
                    (str(source).removeprefix("techqa://"),),
                ).fetchall()
                ranked = sorted(
                    [(float(np.dot(vector[0], np.frombuffer(r[2], dtype="float32"))), r)
                     for r in rows], reverse=True, key=lambda x: x[0],
                )[:request.limit]
                return [{"text": row[0], "metadata": json.loads(row[1]), "score": score}
                        for score, row in ranked]
            scores, ids = self.index.search(vector, request.limit)
            output = []
            for score, identifier in zip(scores[0], ids[0], strict=True):
                if identifier < 0:
                    continue
                row = db.execute("SELECT text,metadata FROM chunks WHERE rowid=?",
                                 (int(identifier) + 1,)).fetchone()
                if row is None:
                    raise ValueError("Missing metadata for semantic result")
                output.append({"text": row[0], "metadata": json.loads(row[1]),
                               "score": float(score)})
            return output


@lru_cache(maxsize=1)
def _searcher() -> SemanticSearch:
    return SemanticSearch(Path(os.getenv("TECHQA_SEMANTIC_PATH", str(SEMANTIC_ROOT))))


def searcher() -> SemanticSearch:
    with INITIALIZATION_LOCK:
        engine = _searcher()
    if os.getenv("TECHQA_PROFILE", "full") != "fixture" and engine.manifest["scope"] != "full":
        raise ValueError("Default serving requires the complete full TechQA corpus")
    return engine


@app.get("/healthz")
def health() -> dict[str, Any]:
    try:
        return searcher().manifest
    except (FileNotFoundError, ValueError, RuntimeError, sqlite3.Error) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/search")
def search(request: SearchRequest) -> dict[str, Any]:
    try:
        engine = searcher()
        return {"embedding_id": engine.manifest["embedding_id"], "results": engine.search(request)}
    except (FileNotFoundError, ValueError, RuntimeError, sqlite3.Error) as exc:
        LOGGER.exception("Semantic search unavailable")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
