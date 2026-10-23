"""Metered wrappers for reused Project 1 components (no Project 1 code is modified)."""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from rag.techqa.index import TechQAIndex
from rag.techqa.retrieval import TechQAReranker

from agents.chap12.budget import CURRENT, charge, deadline_remaining


class MeteredConnection:
    """sqlite3 connection proxy: one `sql` reservation (and deadline check) per statement."""

    def __init__(self, inner: sqlite3.Connection) -> None:
        self.inner = inner

    def execute(self, sql: str, params: Any = ()) -> sqlite3.Cursor:
        charge("sql")
        return self.inner.execute(sql, params)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


@contextmanager
def metered_connection(db: sqlite3.Connection) -> Iterator[MeteredConnection]:
    remaining = deadline_remaining()
    if remaining is not None:
        stop = time.monotonic() + remaining
        db.set_progress_handler(lambda: int(time.monotonic() > stop), 1000)
    yield MeteredConnection(db)


class MeteredIndex(TechQAIndex):
    """TechQAIndex whose every SQL statement is metered and deadline-interruptible."""

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        with super().connect() as db, metered_connection(db) as metered:
            yield metered  # type: ignore[misc]


class CountingReranker(TechQAReranker):
    """Separates nomic embedding cache hits (no call) from misses (charged in the embedder)."""

    async def embeddings(self, texts: list[str]) -> list[list[float]]:
        before = 0
        active = CURRENT.get()
        if active is not None:
            before = active[0].used["embedding"]
        result: list[list[float]] = await super().embeddings(texts)
        if active is not None:
            misses_requested = active[0].used["embedding"] - before
            # One miss request covers all uncached texts; texts not sent are cache hits.
            sent = 0 if misses_requested == 0 else _last_batch_size(self)
            active[0].record_cache_hits(len(texts) - sent)
        return result


def _last_batch_size(reranker: Any) -> int:
    return int(getattr(reranker.embedder, "last_batch_size", 0))
