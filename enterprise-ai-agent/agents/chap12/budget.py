"""Program-enforced request budget: deadline plus per-kind call caps.

A call is reserved *before* it starts; failed, retried or cancelled calls still consume budget.
The current budget/worker travel in ContextVars so shared, already-built Project 1 components
(model, reranker embedder) are metered without rebuilding them per request.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Literal

from pydantic import Field

from agents.chap12.contracts import Strict

# llm: model generations; embedding: nomic embedding requests (cache misses);
# db: logical DB Worker queries/inferences; tool: Worker invocations;
# sql: every individual SQL statement (RAG BM25/parents and DB Worker);
# local: local model compute (MiniLM query encoding).
Kind = Literal["llm", "embedding", "db", "tool", "sql", "local"]


class BudgetExhausted(RuntimeError):
    def __init__(self, kind: str, detail: str) -> None:
        super().__init__(f"{kind} budget exhausted: {detail}")
        self.kind = kind


class BudgetLimits(Strict):
    deadline_seconds: float = Field(default=150, gt=0, le=900)
    max_llm_calls: int = Field(default=8, ge=0, le=64)
    max_embedding_calls: int = Field(default=4, ge=0, le=64)
    max_db_queries: int = Field(default=4, ge=0, le=64)
    max_tool_calls: int = Field(default=4, ge=0, le=64)
    max_sql_statements: int = Field(default=400, ge=0, le=10000)
    max_local_compute: int = Field(default=16, ge=0, le=256)


class Budget:
    def __init__(self, limits: BudgetLimits, clock: Any = time.monotonic) -> None:
        self.limits, self.clock = limits, clock
        self.started = clock()
        self.used: dict[str, int] = {"llm": 0, "embedding": 0, "db": 0, "tool": 0, "sql": 0,
                                     "local": 0}
        # Informational: texts served from the nomic embedding cache (no external call).
        self.embedding_cache_hits = 0
        # Observed model tokens; None until a response actually reports them.
        self.prompt_tokens: int | None = None
        self.completion_tokens: int | None = None
        self.by_worker: dict[str, dict[str, int]] = {}
        self._lock = threading.Lock()

    def cap(self, kind: Kind) -> int:
        return {
            "llm": self.limits.max_llm_calls,
            "embedding": self.limits.max_embedding_calls,
            "db": self.limits.max_db_queries,
            "tool": self.limits.max_tool_calls,
            "sql": self.limits.max_sql_statements,
            "local": self.limits.max_local_compute,
        }[kind]

    def remaining(self) -> float:
        return max(0.0, self.limits.deadline_seconds - self._elapsed())

    def elapsed_ms(self) -> float:
        return self._elapsed() * 1000

    def _elapsed(self) -> float:
        return float(self.clock()) - float(self.started)

    def reserve(self, kind: Kind, worker: str = "supervisor") -> None:
        with self._lock:
            if self.remaining() <= 0:
                raise BudgetExhausted("deadline", f"{self.limits.deadline_seconds}s elapsed")
            if self.used[kind] >= self.cap(kind):
                raise BudgetExhausted(kind, f"call {self.used[kind] + 1} > cap {self.cap(kind)}")
            self.used[kind] += 1
            counts = self.by_worker.setdefault(worker, {k: 0 for k in self.used})
            counts[kind] += 1

    def record_cache_hits(self, count: int) -> None:
        with self._lock:
            self.embedding_cache_hits += count

    def record_tokens(self, prompt: Any, completion: Any) -> None:
        with self._lock:
            if isinstance(prompt, int):
                self.prompt_tokens = (self.prompt_tokens or 0) + prompt
            if isinstance(completion, int):
                self.completion_tokens = (self.completion_tokens or 0) + completion

    def worker_count(self, worker: str, kind: Kind) -> int:
        return self.by_worker.get(worker, {}).get(kind, 0)


CURRENT: ContextVar[tuple[Budget, str] | None] = ContextVar("chap12_budget", default=None)


@contextmanager
def metered(budget: Budget, worker: str) -> Iterator[None]:
    token = CURRENT.set((budget, worker))
    try:
        yield
    finally:
        CURRENT.reset(token)


def charge(kind: Kind) -> None:
    """Reserve against the active request budget. Outside a request (e.g. tests) is a no-op.

    Called immediately before every external or expensive call, including from worker
    threads (asyncio.to_thread copies the context). After the deadline it raises, so a thread
    abandoned by a cancelled coroutine cannot start any further call."""
    active = CURRENT.get()
    if active is not None:
        active[0].reserve(kind, active[1])


def deadline_remaining() -> float | None:
    active = CURRENT.get()
    return None if active is None else active[0].remaining()


class BudgetedModel:
    """StructuredModel proxy: reserves one LLM call before each generation."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner

    async def generate(self, prompt: str, schema: dict[str, Any]) -> str:
        charge("llm")
        result: str = await self.inner.generate(prompt, schema)
        return result


class BudgetedEmbedder:
    """Reranker embedding proxy: one reservation per embedding batch request."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        charge("embedding")
        self.last_batch_size = len(texts)
        result: list[list[float]] = await self.inner.embed_documents(texts)
        return result
