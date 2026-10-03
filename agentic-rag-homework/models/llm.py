"""Structured model adapters plus exact call/token instrumentation."""

from __future__ import annotations

import json
import os
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
            model_errors=self.metrics.model_errors - before.model_errors,
            input_tokens=self.metrics.input_tokens - before.input_tokens,
            output_tokens=self.metrics.output_tokens - before.output_tokens,
        )

    async def generate(self, prompt: str, schema: dict[str, Any]) -> str:
        self.metrics.llm_calls += 1
        self.metrics.input_tokens += token_count(prompt)
        try:
            output = await self.inner.generate(prompt, schema)
        except Exception:
            self.metrics.model_errors += 1
            raise
        self.outputs.append(output)
        self.metrics.output_tokens += token_count(output)
        return output


class OllamaStructuredModel:
    def __init__(self, model: str | None = None, url: str = "http://localhost:11434",
                 num_gpu: int | None = None) -> None:
        self.model = model or os.getenv("OLLAMA_MODEL") or "qwen2.5:7b"
        self.url = url.rstrip("/")
        self.num_gpu = num_gpu

    async def generate(self, prompt: str, schema: dict[str, Any]) -> str:
        budget = 1200
        if prompt.startswith(("KIND: EVIDENCE_SELECTOR\n", "KIND: GROUNDED_DIAGNOSIS\n")):
            budget = 180
        elif prompt.startswith("KIND: REACT\n"):
            budget = 400
        elif prompt.startswith("KIND: CRITIC\n"):
            budget = 512
        elif prompt.startswith("KIND: DIAGNOSIS\n"):
            budget = 800
        options = {"temperature": 0, "num_predict": budget, "num_ctx": 8192}
        gpu = self.num_gpu
        if gpu is None and "OLLAMA_NUM_GPU" in os.environ:
            gpu = int(os.environ["OLLAMA_NUM_GPU"])
        if gpu is not None:
            options.update({"num_gpu": gpu, "num_thread": 4})
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                self.url + "/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "format": schema,
                    "messages": [{"role": "user", "content": prompt}],
                    "options": options,
                },
            )
            response.raise_for_status()
            result = response.json()
            if result.get("done_reason") == "length":
                raise ValueError(f"Structured generation exceeded token budget {budget}")
            return str(result["message"]["content"])


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
