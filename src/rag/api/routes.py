"""Dependency-injected FastAPI routes for the production RAG service."""

# mypy: disable-error-code="misc,untyped-decorator"

from __future__ import annotations

from typing import Any

from rag.generation.service import RAGService


def create_app(*, service: RAGService) -> Any:
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel, Field
    except ImportError as exc:
        raise RuntimeError("Install the 'api' extra to use the HTTP API") from exc

    app = FastAPI(title="AWS Support RAG", version="0.2.0")

    class QueryRequest(BaseModel):
        query: str = Field(min_length=1, max_length=2_000)
        mode: str = Field(default="hybrid", pattern="^(dense|sparse|hybrid)$")
        filters: dict[str, str | int | float | bool] | None = None

    @app.post("/v1/rag/query")
    async def query(request: QueryRequest) -> dict[str, Any]:
        try:
            response = await service.query(
                request.query,
                mode=request.mode,  # type: ignore[arg-type]
                filters=request.filters,
            )
            return response.to_dict()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Retrieval service unavailable") from exc

    return app
