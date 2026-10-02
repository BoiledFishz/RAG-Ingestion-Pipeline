"""Dependency-injected FastAPI routes for the production RAG service."""

# mypy: disable-error-code="misc,untyped-decorator"

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from rag.generation.service import RAGService
from rag.ingestion.models import MetadataValue
from rag.retrieval.contracts import RetrievalMode

LOGGER = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)
    mode: RetrievalMode = "hybrid"
    filters: dict[str, MetadataValue] | None = None


def create_app(*, service: RAGService) -> Any:
    try:
        from fastapi import FastAPI, HTTPException, Response
    except ImportError as exc:
        raise RuntimeError("Install the 'api' extra to use the HTTP API") from exc

    app = FastAPI(title="IBM TechQA RAG", version="0.3.0")

    @app.post("/v1/rag/query")
    async def query(request: QueryRequest) -> Any:
        try:
            response = await service.query(
                request.query,
                mode=request.mode,
                filters=request.filters,
            )
            return Response(
                content=json.dumps(response.to_dict(), ensure_ascii=False),
                media_type="application/json; charset=utf-8",
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            LOGGER.exception("RAG query failed")
            raise HTTPException(status_code=503, detail="Retrieval service unavailable") from exc

    return app
