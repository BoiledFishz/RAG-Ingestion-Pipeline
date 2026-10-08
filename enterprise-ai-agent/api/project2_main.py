"""Versioned Project 2 entry; old API and MultiAgent defaults are untouched."""

from __future__ import annotations

import json
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from agents.project2.budget import Budget, prepare_budget_configuration
from agents.project2.policy import TrustedContext
from agents.project2.rag_process import BoundedRAGProcess
from agents.project2.supervisor import Supervisor, empty_result, response
from models.project2 import AnalysisRequest
from tools.techqa_document_query import DatabaseWorker

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]


class RequestBudgetBoundary:
    """Direct ASGI cancellation; a detached BaseHTTPMiddleware task is unsafe."""
    def __init__(self, app: Any, runtime: BoundedRAGProcess) -> None:
        self.app, self.runtime = app, runtime

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        budget = Budget()
        scope.setdefault("state", {})["budget"] = budget
        started = False

        async def bounded_send(message: dict) -> None:
            nonlocal started
            budget.remaining()
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            async with asyncio.timeout(budget.remaining()):
                await self.app(scope, receive, bounded_send)
        except TimeoutError:
            budget.cancel()
            # A running request owns the isolated child; terminate outstanding work.
            self.runtime.cancel_request(budget)
            LOGGER.warning("Project2 HTTP deadline cancelled attempts=%d", budget.attempts)
            if started:
                raise
            rid = getattr(budget, "run_id", None) or uuid4().hex
            database = getattr(budget, "database_result", None) or empty_result("database", "timeout", rid, "request_deadline_exhausted")
            rag = empty_result("rag", "timeout", rid, "request_deadline_exhausted")
            output = JSONResponse(content=response(rid, rag, database, budget))
            await output(scope, receive, send)


def server_credentials() -> dict[str, TrustedContext]:
    # Credentials are server configuration, never values granting request authority.
    raw = os.getenv("PROJECT2_CREDENTIALS_JSON", "{}")
    entries = json.loads(raw)
    return {token: TrustedContext(value["subject_id"], value["tenant_id"], frozenset(value["allowed_corpus_scopes"]), frozenset(value["allowed_operations"]))
            for token, value in entries.items()}


def create_app(*, credentials: dict[str, TrustedContext] | None = None, warmup: bool = True) -> FastAPI:
    prepare_budget_configuration()
    environment = json.loads((ROOT / "evals/protocol_v0/baseline_v0.config.json").read_text(encoding="utf-8"))["environment"]
    runtime = BoundedRAGProcess(environment)
    runtime.startup_required=warmup
    database = DatabaseWorker(ROOT / ".rag_data/techqa_full.sqlite")
    supervisor = Supervisor(database, runtime, registered_database_path=ROOT / ".rag_data/techqa_full.sqlite")
    tokens = server_credentials() if credentials is None else dict(credentials)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async def maintain_readiness():
            # One bounded initialization per lost Worker. No request or run budget
            # is in this task; failed initialization leaves the service unready.
            while True:
                await asyncio.sleep(.1)
                if not runtime.active:
                    try:await runtime.start()
                    except Exception:
                        LOGGER.exception('Project2 background readiness failed; service remains unready')
                        return
        if warmup:
            await runtime.start()
        readiness=asyncio.create_task(maintain_readiness()) if warmup else None
        try:yield
        finally:
            if readiness:
                readiness.cancel()
                try:await readiness
                except asyncio.CancelledError:pass
            runtime.stop()

    app = FastAPI(title="TechQA Project 2 v1", lifespan=lifespan)
    app.state.supervisor, app.state.rag_runtime = supervisor, runtime

    app.add_middleware(RequestBudgetBoundary, runtime=runtime)

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, error: RequestValidationError):
        run_id = uuid4().hex
        LOGGER.warning('P2_INVALID_INPUT trace_id=%s fields=%s',run_id,
                       [list(item['loc']) for item in error.errors()])
        return JSONResponse(status_code=422, content=response(run_id, empty_result("rag", "failed", run_id, "invalid_input"), empty_result("database", "failed", run_id, "invalid_input"), request.state.budget))

    @app.get("/healthz")
    async def health() -> dict[str, Any]:
        return {"alive": True, "ready": runtime.active and runtime.ready, "contract_version": "project2-v1"}

    @app.post("/v1/project2/analysis")
    async def analyze(request: Request, body: AnalysisRequest) -> dict[str, Any]:
        header = request.headers.get("authorization", "")
        credential = header.removeprefix("Bearer ") if header.startswith("Bearer ") else ""
        context = tokens.get(credential)
        return await supervisor.run(body, context, request.state.budget)

    return app


app = create_app()
