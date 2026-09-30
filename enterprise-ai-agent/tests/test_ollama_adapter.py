from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import pytest

from models.errors import DependencyUnavailable
from models.providers import OllamaStructuredModel
from models.schemas import RewriteDraft


def test_ollama_sends_json_schema_and_parses_content(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": '{"query":"S3 AccessDenied","action":"retrieve","clarification":""}'
                }
            },
        )

    original_client = httpx.AsyncClient

    def client_factory(**kwargs: Any) -> httpx.AsyncClient:
        return original_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)
    model = OllamaStructuredModel("http://localhost:11434", "llama3.2:3b")
    result = asyncio.run(model.generate("rewrite", RewriteDraft.model_json_schema()))
    assert RewriteDraft.model_validate_json(result).action == "retrieve"
    assert isinstance(captured["format"], dict)
    assert set(captured["format"]["required"]) == {"query", "action", "clarification"}
    assert "fallback" not in captured["format"]["properties"]
    assert captured["stream"] is False


def test_ollama_http_error_is_dependency_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    original_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "busy"})

    def client_factory(**kwargs: Any) -> httpx.AsyncClient:
        return original_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)
    with pytest.raises(DependencyUnavailable):
        asyncio.run(OllamaStructuredModel("http://local", "model").generate("test", {}))
