"""FastAPI lifespan owns resources; only the three-field contract is public."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from agents.rag_agent.factory import build_agent, open_store
from agents.rag_agent.service import RAGAgent
from models.errors import DependencyUnavailable
from models.schemas import AgentResponse, QueryRequest
from models.settings import Settings

LOGGER = logging.getLogger(__name__)


class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


def create_app(agent: RAGAgent | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if agent is not None:
            app.state.agent = agent
            yield
            return
        settings = Settings.from_env()
        store = open_store(settings)
        try:
            app.state.agent = build_agent(settings, store)
            LOGGER.info(
                "Agent started profile=%s collection=%s", settings.profile, settings.collection
            )
            yield
        finally:
            await store.close()

    app = FastAPI(
        title="Enterprise RAG Agent",
        version="0.1.0",
        lifespan=lifespan,
        default_response_class=UTF8JSONResponse,
    )
    if agent is not None:
        app.state.agent = agent

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        # Liveness only; this does not claim model/database readiness.
        return {"status": "ok"}

    @app.post("/v1/agent/query", response_model=AgentResponse)
    async def query(body: QueryRequest, request: Request) -> AgentResponse:
        service: RAGAgent = request.app.state.agent
        try:
            return (await service.run(body)).response
        except DependencyUnavailable as exc:
            LOGGER.exception("Agent dependency unavailable")
            raise HTTPException(status_code=503, detail="Agent dependency unavailable") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            LOGGER.exception("Unexpected agent error")
            raise HTTPException(status_code=500, detail="Internal agent error") from exc

    return app


app = create_app()
