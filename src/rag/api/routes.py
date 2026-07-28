"""FastAPI route factory kept dependency-injected for testability."""

# mypy: disable-error-code="misc,untyped-decorator"

from __future__ import annotations

from typing import Any

from rag.generation.generator import OllamaGenerator
from rag.retrieval.context_builder import ContextBuilder
from rag.retrieval.pipeline import HybridRetriever


def create_app(
    *,
    retriever: HybridRetriever,
    generator: OllamaGenerator,
    context_builder: ContextBuilder | None = None,
) -> Any:
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel, Field
    except ImportError as exc:
        raise RuntimeError("Install the 'api' extra to use the HTTP API") from exc

    builder = context_builder or ContextBuilder()
    app = FastAPI(title="AWS Support RAG", version="0.1.0")

    class QueryRequest(BaseModel):
        question: str = Field(min_length=1, max_length=2_000)
        top_k: int = Field(default=5, ge=1, le=20)

    @app.post("/query")
    async def query(request: QueryRequest) -> dict[str, Any]:
        try:
            results = await retriever.retrieve(request.question, limit=request.top_k)
            context = builder.build(results)
            answer = await generator.generate(question=request.question, context=context)
            return {
                "answer": answer,
                "sources": [
                    {
                        "source_file": item.metadata.get("source_file"),
                        "page_number": item.metadata.get("page_number"),
                        "chunk_hash": item.chunk_hash,
                        "score": item.score,
                    }
                    for item in results
                ],
            }
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Retrieval service unavailable") from exc

    return app
