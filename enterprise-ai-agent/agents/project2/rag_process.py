"""Isolate reused native RAG so SQL/model attempts and cancellation are real.

The child receives query only, never QA IDs, target IDs, answers or labels.
Instrumentation is process-local; existing services and MultiAgent defaults
are not monkey-patched. A cancelled request terminates this isolated child.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from threading import RLock
from typing import Any

from agents.project2.budget import Budget, BudgetExceeded

LOGGER = logging.getLogger(__name__)
_REQUEST_BUDGET: Any = None
_CONNECT = sqlite3.connect

def dependency_timeout(error: BaseException) -> bool:
    """Retain a wrapped transport timeout across this isolated process boundary."""
    import httpx
    seen=set();pending=[error]
    while pending:
        current=pending.pop()
        if id(current) in seen:continue
        seen.add(id(current))
        if isinstance(current,(TimeoutError,httpx.TimeoutException)):return True
        pending.extend(x for x in (current.__cause__,current.__context__) if x is not None)
    return False


class BudgetConnection(sqlite3.Connection):
    request_budget: Any = None

    def _reserve(self) -> None:
        active = self.request_budget or _REQUEST_BUDGET
        if active is None:
            return
        active.reserve("db")
        started = time.monotonic()
        remaining = active.remaining(12)
        self.set_progress_handler(lambda: int(time.monotonic()-started >= remaining), 1000)

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        self._reserve()
        return super().execute(*args, **kwargs)

    def executemany(self, *args: Any, **kwargs: Any) -> Any:
        sql, parameters = args
        cursor = None
        for values in parameters:
            cursor = self.execute(sql, values, **kwargs)
        return cursor

    def commit(self) -> None:
        if self.in_transaction:
            self._reserve()
        super().commit()

    def executescript(self, *args: Any, **kwargs: Any) -> Any:
        raise ValueError("Unbounded scripts are not registered Project 2 dependencies")

    def cursor(self, *args: Any, **kwargs: Any) -> Any:
        raise ValueError("Project 2 dependency must use instrumented Connection.execute")


def guarded_connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
    kwargs["factory"] = BudgetConnection
    if _REQUEST_BUDGET is not None:
        kwargs["timeout"] = _REQUEST_BUDGET.remaining(12)
    return _CONNECT(*args, **kwargs)


class RemoteBudget:
    def __init__(self, deadline: float) -> None:
        self.deadline = deadline
        self.lock = RLock()
        self.exceeded = False
        self.denial_reason: str | None = None

    def remaining(self, local_limit: float | None = None) -> float:
        value = self.deadline - time.time()
        if value <= 0 or self.exceeded:
            raise BudgetExceeded("request_deadline_or_attempt_limit")
        return value if local_limit is None else min(value, local_limit)

    def reserve(self, kind: str) -> None:
        with self.lock:
            self.remaining()
            sys.stdout.write(json.dumps({"type": "reserve", "kind": kind}) + "\n")
            sys.stdout.flush()
            response = json.loads(sys.stdin.readline())
            if response.get("allowed") is not True:
                self.exceeded = True
                self.denial_reason = response.get("reason", "dependency_budget")
                raise BudgetExceeded(response.get("reason", "dependency_budget"))


class EncoderModelProxy:
    def __init__(self, original: Any) -> None:
        self.original = original

    def __getattr__(self, key: str) -> Any:
        return getattr(self.original, key)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if _REQUEST_BUDGET is not None:
            _REQUEST_BUDGET.reserve("embedding")
        return self.original(*args, **kwargs)


class LocalDense:
    def __init__(self, engine: Any, policy: Any) -> None:
        self.engine, self.policy = engine, policy

    async def retrieve(self, query: str, *, limit: int = 30, filters: Any = None) -> Any:
        from rag.retrieval.contracts import SearchResult
        from rag.techqa.embedding_server import SearchRequest

        secured = self.policy.apply(filters)
        rows = await asyncio.to_thread(self.engine.search, SearchRequest(query=query, limit=limit, filters=secured))
        return [SearchResult(text=row["text"], metadata=row["metadata"], score=row["score"], backend="dense",
                             retrieval_rank=rank, retrieval_score=row["score"], dense_rank=rank, retrieval_sources=("dense",))
                for rank, row in enumerate(rows, 1)]


def child_main() -> int:
    global _REQUEST_BUDGET
    entered=time.perf_counter()
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    # Isolated process only; no global changes in any existing application.
    sqlite3.connect = guarded_connect
    import httpx

    original_send = httpx.AsyncClient.send

    async def measured_send(client: Any, request: Any, *args: Any, **kwargs: Any) -> Any:
        if _REQUEST_BUDGET is not None:
            _REQUEST_BUDGET.reserve("llm" if request.url.path == "/api/chat" else "embedding_http" if request.url.path == "/api/embed" else "http")
            seconds = _REQUEST_BUDGET.remaining(30)
            request.extensions["timeout"] = {key: seconds for key in ("connect", "read", "write", "pool")}
        return await original_send(client, request, *args, **kwargs)

    httpx.AsyncClient.send = measured_send
    try:
        imports_started=time.perf_counter()
        from agents.rag_agent.factory import build_agent
        from models.schemas import QueryRequest
        from models.settings import Settings
        from rag.retrieval.filters import FilterPolicy
        from rag.techqa.semantic import SEMANTIC_ROOT
        from agents.project2.batched_retrieval import BatchedIndex, BatchedParents, BatchedReranker, BatchedSemanticSearch

        imported=time.perf_counter()
        agent = build_agent(Settings.from_env())
        built=time.perf_counter()
        # Observability only: no file, candidate, score or returned value changes.
        import faiss
        original_read=faiss.read_index;index_seconds=[]
        def measured_index_read(*args,**kwargs):
            started=time.perf_counter()
            try:return original_read(*args,**kwargs)
            finally:index_seconds.append(time.perf_counter()-started)
        faiss.read_index=measured_index_read
        try:engine = BatchedSemanticSearch(SEMANTIC_ROOT)
        finally:faiss.read_index=original_read
        loaded=time.perf_counter()
        from agents.project2.startup_warmup import warm_engine
        warmup=warm_engine(engine,Path(__file__).resolve().parents[3]/'.rag_data/techqa_full.sqlite')
        engine.encoder.model = EncoderModelProxy(engine.encoder.model)
        agent.retriever.pipeline.dense = LocalDense(engine, FilterPolicy())
        index = BatchedIndex(agent.retriever.pipeline.sparse.index.path)
        agent.retriever.pipeline.sparse.index = index
        agent.retriever.parents = BatchedParents(index)
        old_reranker = agent.retriever.pipeline.reranker
        agent.retriever.pipeline.reranker = BatchedReranker(old_reranker.semantic, weights=old_reranker.weights)
        from agents.project2.observability import observe_pipeline
        pipeline_measurement: dict[str, Any] = {}
        observe_pipeline(agent.retriever.pipeline, pipeline_measurement)
        sys.stdout.write(json.dumps({"type": "ready", "scope": engine.manifest["scope"], "embedding_id": engine.manifest["embedding_id"],
             "worker_pid":os.getpid(),"warmup":warmup,"startup_timings":{"imports_seconds":imported-imports_started,
                "agent_build_seconds":built-imported,"index_and_encoder_seconds":loaded-built,
                "faiss_index_load_seconds":sum(index_seconds),"child_initialization_seconds":time.perf_counter()-entered}}) + "\n")
        sys.stdout.flush()
        while line := sys.stdin.readline():
            command = json.loads(line)
            if set(command) != {"query", "absolute_deadline"}:
                raise ValueError("Only original query and trusted parent deadline may enter RAG")
            _REQUEST_BUDGET = RemoteBudget(command["absolute_deadline"])
            pipeline_measurement.clear()
            try:
                # New outer request already validates type/size; preserve whitespace.
                request = QueryRequest.model_construct(query=command["query"], filters={})
                result = asyncio.run(agent.run(request))
                message = {"type": "result", "data": result.model_dump(mode="json"), "pipeline": dict(pipeline_measurement), "budget_exceeded": _REQUEST_BUDGET.exceeded, "budget_exceeded_reason": _REQUEST_BUDGET.denial_reason}
            except Exception as exc:
                LOGGER.exception("Project 2 isolated RAG failed")
                message = {"type": "error", "category": type(exc).__name__, "detail": str(exc)[:500], "dependency_timeout":dependency_timeout(exc), "budget_exceeded": _REQUEST_BUDGET.exceeded, "budget_exceeded_reason": _REQUEST_BUDGET.denial_reason}
            _REQUEST_BUDGET = None
            sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    except Exception as exc:
        LOGGER.exception("Project 2 RAG initialization failed")
        sys.stdout.write(json.dumps({"type": "startup_error", "detail": str(exc)[:500]}) + "\n")
        sys.stdout.flush()
        return 1
    return 0


class BoundedRAGProcess:
    input_fields = frozenset({"query"})

    def __init__(self, environment: dict[str, str]) -> None:
        self.environment = dict(environment)
        self.model = self.environment["AGENT_MODEL"]
        self.process: subprocess.Popen[str] | None = None
        self.lock = asyncio.Lock()
        self.active_budget: Budget | None = None
        self.startup_task: asyncio.Task[dict[str, Any]] | None = None
        self.ready = False
        self.startup_required = False
        self.startup_observation: dict[str,Any]={}
        self.cleanup_observation: dict[str,Any]={}

    @property
    def active(self) -> bool:
        return self.process is not None and self.process.poll() is None

    async def start(self) -> dict[str, Any]:
        if self.active and self.ready:
            return {"type": "ready"}
        if self.startup_task is None or self.startup_task.done():
            self.startup_task = asyncio.create_task(self._start())
        # Index/model initialization is shared service readiness, with no user
        # query and no LLM calls. A waiting request cannot restart it indefinitely.
        return await asyncio.shield(self.startup_task)

    async def _start(self) -> dict[str, Any]:
        root = Path(__file__).resolve().parents[3]
        python = root / ".venv312/Scripts/python.exe"
        if not python.is_file():
            raise FileNotFoundError("Native local Python runtime absent; no install permitted")
        env = {**os.environ, **self.environment, "PYTHONIOENCODING": "utf-8", "PYTHONPATH": str(root / "src")+os.pathsep+str(root / "enterprise-ai-agent"), "TECHQA_QUERY_DEVICE": "cpu"}
        log = root / "audit/project2-v1/rag_child.stderr.log"
        with log.open("a", encoding="utf-8") as stderr:
            launched=time.perf_counter()
            self.process = subprocess.Popen([str(python), "-m", "agents.project2.rag_process", "--worker"], cwd=root / "enterprise-ai-agent", env=env,
                                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr, text=True, encoding="utf-8", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            # Service cold-start readiness is separate from request deadlines.
            # Runtime.run still bounds an on-demand restart by remaining budget.
            response = json.loads(await asyncio.wait_for(asyncio.to_thread(self.process.stdout.readline), 180))
            if response.get("type") != "ready" or response.get("scope") != "full":
                raise RuntimeError(f"Native RAG startup failed: {response}")
            self.ready = True
            self.startup_observation={**response,"launch_to_ready_seconds":time.perf_counter()-launched}
            LOGGER.info('P2_STARTUP %s',json.dumps(self.startup_observation))
            return response
        except Exception:
            self.stop()
            raise

    def stop(self) -> None:
        started=time.perf_counter();mode='already_stopped'
        self.ready = False
        startup, self.startup_task = self.startup_task, None
        try: current = asyncio.current_task()
        except RuntimeError: current = None
        if startup is not None and not startup.done() and startup is not current:
            startup.cancel()
        if self.process is not None:
            # An idle worker exits on EOF. Do not ask a separate utility to open
            # another process when our existing owned pipe suffices.
            if self.active and self.active_budget is None and self.process.stdin:
                self.process.stdin.close()
                try:
                    self.process.wait(timeout=2);mode='idle_eof'
                except subprocess.TimeoutExpired:pass
            if self.active:
                mode='owned_force_cancel'
                if os.name == 'nt':
                    # venv redirectors can own a separate interpreter. Terminating only
                    # the redirector leaves the actual worker and its pipes alive.
                    stopped = subprocess.run([os.path.join(os.environ['WINDIR'], 'System32', 'taskkill.exe'),
                                              '/PID', str(self.process.pid), '/T', '/F'],
                                             capture_output=True, timeout=5,
                                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                    if stopped.returncode != 0 and self.process.poll() is None:
                        detail=(stopped.stderr or stopped.stdout or b'').decode('mbcs',errors='replace')
                        raise RuntimeError('Owned RAG process tree could not be cancelled: '+detail[:250])
                else:
                    self.process.terminate()
                self.process.wait(timeout=10)
            for stream in (self.process.stdin, self.process.stdout):
                if stream:
                    stream.close()
            self.process = None
        self.cleanup_observation={'mode':mode,'elapsed_seconds':time.perf_counter()-started,'process_retained':self.process is not None}
        LOGGER.info('P2_CLEANUP %s',json.dumps(self.cleanup_observation))

    def cancel_request(self, budget: Budget) -> None:
        if self.active_budget is budget:
            self.stop()

    async def run(self, query: str, budget: Budget) -> dict[str, Any]:
        acquired = False
        query_sent = False
        try:
            remaining = budget.remaining()
            await asyncio.wait_for(self.lock.acquire(), remaining)
            acquired = True
            try:
                if self.startup_required and not (self.active and self.ready):
                    raise RuntimeError('worker_not_ready')
                remaining = budget.remaining()
                if not self.startup_required:
                    await asyncio.wait_for(self.start(), remaining)
                budget.remaining()
                self.active_budget = budget
                query_sent = True
                self.process.stdin.write(json.dumps({"query": query, "absolute_deadline": budget.absolute_deadline}) + "\n")
                self.process.stdin.flush()
                while True:
                    raw = await asyncio.wait_for(asyncio.to_thread(self.process.stdout.readline), budget.remaining())
                    if not raw:
                        raise RuntimeError("Native RAG process stopped unexpectedly")
                    message = json.loads(raw)
                    if message["type"] == "reserve":
                        try:
                            budget.reserve(message["kind"])
                            reply = {"allowed": True}
                        except BudgetExceeded as exc:
                            reply = {"allowed": False, "reason": str(exc)}
                        self.process.stdin.write(json.dumps(reply) + "\n")
                        self.process.stdin.flush()
                    else:
                        if message.get('type')=='error' and message.get('dependency_timeout') is True:
                            raise TimeoutError(message.get('category','dependency_timeout'))
                        return message
            except (TimeoutError, RuntimeError, asyncio.CancelledError):
                if query_sent:
                    self.stop()
                raise
        finally:
            if acquired:
                self.active_budget = None
                self.lock.release()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(child_main())
