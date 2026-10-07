"""New versioned Runtime entry. Existing Project2 and MultiAgent entries remain."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from api.project2_main import create_app as legacy_app, server_credentials, ROOT
from agents.project2.service_runtime import RuntimeCoordinator, StateStore, RuntimeRejected
from agents.project2.budget import BudgetExceeded
from agents.project2.policy import TrustedContext
from typing import Any
from agents.project2.supervisor import empty_result, response
from uuid import uuid4
import re
from models.project2 import AnalysisRequest
from agents.project2.execution_clock import ExecutionLedgerBoundary,load_policy


def runtime_version() -> str:
    paths = [ROOT/'evals/protocol_v0/baseline_v0.config.json',
             ROOT/'evals/project2-v1/calibration_v031/budget_frozen.json',
             ROOT/'enterprise-ai-agent/tools/techqa_document_query.py',
             ROOT/'specs/project2/v0.3.3/recovery_accounting.json']
    return hashlib.sha256(b''.join(path.read_bytes() for path in paths)).hexdigest()


def create_app(*, credentials: dict[str,TrustedContext] | None=None, warmup: bool=True, state_directory: Path | None=None) -> FastAPI:
    app = legacy_app(credentials=credentials, warmup=warmup)
    tokens = server_credentials() if credentials is None else dict(credentials)
    store = StateStore(state_directory or Path(os.getenv('PROJECT2_STATE_DIRECTORY', str(ROOT/'.rag_data/project2_runtime'))), runtime_version(),execution_policy=load_policy(ROOT,'v0.3.3'))
    runtime = RuntimeCoordinator(app.state.supervisor, store)
    # This app instance only: both default and versioned paths enforce Runtime.
    app.state.supervisor.run = runtime.analyze
    app.state.service_runtime = runtime;app.state.state_store = store
    app.title='TechQA Project 2 Runtime v2'
    app.add_middleware(ExecutionLedgerBoundary)

    def context(request: Request) -> TrustedContext | None:
        header=request.headers.get('authorization', '')
        return tokens.get(header[7:]) if header.startswith('Bearer ') else None

    def rejection(error: Exception, request: Request, run_id: str | None=None) -> JSONResponse:
        category=str(error)
        code=403 if category=='permission_denied' else 404 if category=='unknown_run' else 409
        status='permission_denied' if code==403 else 'timeout' if isinstance(error, TimeoutError) or category=='state_expired' else 'failed'
        rid=run_id if run_id and re.fullmatch(r'[0-9a-f]{32}',run_id) else uuid4().hex
        result=response(rid,empty_result('rag',status,rid,category),empty_result('database',status,rid,category),request.state.budget)
        result['error']=category
        return JSONResponse(status_code=code,content=result)

    @app.exception_handler(RuntimeRejected)
    async def runtime_error(request: Request, error: RuntimeRejected) -> JSONResponse:
        return rejection(error,request)

    @app.post('/v2/project2/analysis')
    async def analysis(request: Request, body: AnalysisRequest) -> Any:
        try:return await runtime.analyze(body, context(request), request.state.budget)
        except RuntimeRejected as error:return rejection(error,request)

    @app.get('/v2/project2/runs/{run_id}')
    async def read_run(request: Request, run_id: str) -> Any:
        try:
            state=store.load(run_id, context(request))
            return {'run_id':run_id, 'lifecycle':state['lifecycle'], 'budget':state['budget'],
                    'node_statuses':{key:value['status'] for key,value in state['nodes'].items()}, 'result':state['result']}
        except RuntimeRejected as error:return rejection(error,request,run_id)

    @app.post('/v2/project2/runs/{run_id}/resume')
    async def resume(request: Request, run_id: str) -> Any:
        try:return await runtime.resume(run_id, context(request), request.state.budget)
        except (RuntimeRejected, BudgetExceeded) as error:return rejection(error,request,run_id)

    @app.get('/v2/project2/runs/{run_id}/trace')
    async def trace(request: Request, run_id: str) -> Any:
        try:return {'run_id':run_id, 'events':store.read_trace(run_id, context(request))}
        except RuntimeRejected as error:return rejection(error,request,run_id)
    return app


app = create_app()
