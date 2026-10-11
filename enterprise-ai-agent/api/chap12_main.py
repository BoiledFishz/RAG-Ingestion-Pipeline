"""Chap12 versioned API: POST /v1/chap12/analyze. The original api.main is untouched.

Credentials are configured server-side in CHAP12_CREDENTIALS_JSON as
{"<sha256 of bearer token>": {"subject_id": ..., "tenant_id": ..., "allowed_workers": [...],
 "allowed_db_operations": [...], "allowed_product_ids": ["*"]}}. The body never grants rights.
"""

# No `from __future__ import annotations`: FastAPI must resolve the closure dependency.
import hashlib
import hmac
import json
import os
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException

from agents.chap12.contracts import AnalysisRequest, FinalResponse, TrustedContext


def load_credentials(raw: str | None = None) -> dict[str, TrustedContext]:
    data: dict[str, Any] = json.loads(raw if raw is not None else
                                      os.getenv("CHAP12_CREDENTIALS_JSON", "{}"))
    return {key.lower(): TrustedContext.model_validate(value) for key, value in data.items()}


def create_app(supervisor_factory: Callable[[], Any] | None = None,
               credentials: dict[str, TrustedContext] | None = None) -> FastAPI:
    app = FastAPI(title="Chap12 Supervisor-Worker", version="chap12-v1")
    state: dict[str, Any] = {}

    def supervisor() -> Any:
        if "supervisor" not in state:
            if supervisor_factory is None:
                from agents.chap12.factory import build_supervisor
                state["supervisor"] = build_supervisor()
            else:
                state["supervisor"] = supervisor_factory()
        return state["supervisor"]

    def context(authorization: Annotated[str | None, Header()] = None) -> TrustedContext:
        table = credentials if credentials is not None else load_credentials()
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "missing bearer credential")
        digest = hashlib.sha256(authorization.removeprefix("Bearer ").encode()).hexdigest()
        for key, ctx in table.items():
            if hmac.compare_digest(key, digest):
                return ctx
        raise HTTPException(401, "unknown credential")

    @app.get("/healthz")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/chap12/analyze", response_model=FinalResponse)
    async def analyze(request: AnalysisRequest,
                      ctx: Annotated[TrustedContext, Depends(context)]) -> FinalResponse:
        result: FinalResponse = await supervisor().run(request, ctx)
        return result

    return app


app = create_app()
