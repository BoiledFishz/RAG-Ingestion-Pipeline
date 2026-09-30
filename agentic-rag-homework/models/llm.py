"""Structured model adapters plus exact call/token instrumentation."""

from __future__ import annotations

import json
import re
from typing import Any, Protocol

import httpx

from models.schemas import Metrics


def token_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9_:/.-]+|[\u4e00-\u9fff]|[^\s]", text))


class StructuredModel(Protocol):
    async def generate(self, prompt: str, schema: dict[str, Any]) -> str: ...


class MeteredModel:
    def __init__(self, inner: StructuredModel) -> None:
        self.inner = inner
        self.metrics = Metrics()
        self.outputs: list[str] = []

    def snapshot(self) -> Metrics:
        return self.metrics.model_copy()

    def delta(self, before: Metrics) -> Metrics:
        return Metrics(
            llm_calls=self.metrics.llm_calls - before.llm_calls,
            input_tokens=self.metrics.input_tokens - before.input_tokens,
            output_tokens=self.metrics.output_tokens - before.output_tokens,
        )

    async def generate(self, prompt: str, schema: dict[str, Any]) -> str:
        self.metrics.llm_calls += 1
        self.metrics.input_tokens += token_count(prompt)
        output = await self.inner.generate(prompt, schema)
        self.outputs.append(output)
        self.metrics.output_tokens += token_count(output)
        return output


class OllamaStructuredModel:
    def __init__(self, model: str = "llama3.2:3b", url: str = "http://localhost:11434") -> None:
        self.model, self.url = model, url.rstrip("/")

    async def generate(self, prompt: str, schema: dict[str, Any]) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                self.url + "/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "format": schema,
                    "messages": [{"role": "user", "content": prompt}],
                    "options": {"temperature": 0},
                },
            )
            response.raise_for_status()
            return str(response.json()["message"]["content"])


class ScriptedModel:
    """Test double used to prove validation, retries and feedback propagation."""

    def __init__(self, outputs: list[dict[str, Any] | str]) -> None:
        self.outputs = list(outputs)
        self.prompts: list[str] = []

    async def generate(self, prompt: str, schema: dict[str, Any]) -> str:
        self.prompts.append(prompt)
        if not self.outputs:
            raise RuntimeError("no scripted output")
        value = self.outputs.pop(0)
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
