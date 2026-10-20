"""Opt-in per-request layer trace (2026-10-20, requested to locate failures by layer).

When a recorder is active (evaluation --trace), the Project 2 components copy what each layer
actually produced into it: retrieval stages (dense, sparse, RRF fusion, rerank, final), the
documents the retriever tool handed to the agent with their score and acceptance threshold,
the RAG agent's rewrite / evidence / status, and the Supervisor trace. Nothing is recomputed
and no ranking, filtering or model call changes; with no recorder active every hook is a no-op.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

RECORDER: ContextVar[dict[str, Any] | None] = ContextVar("chap12_trace", default=None)


@contextmanager
def recording() -> Iterator[dict[str, Any]]:
    data: dict[str, Any] = {}
    token = RECORDER.set(data)
    try:
        yield data
    finally:
        RECORDER.reset(token)


def active() -> dict[str, Any] | None:
    return RECORDER.get()


def record(key: str, value: Any) -> None:
    data = RECORDER.get()
    if data is not None:
        data[key] = value
