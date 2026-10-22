"""Ollama structured model that also reports token usage (P0-4).

The Project 1 adapter `models.providers.OllamaStructuredModel` returns only the content and
discards `prompt_eval_count` / `eval_count`. Project 1 code is not modified: this subclass
repeats the same request (same endpoint, schema, options and per-prompt output budgets) and
additionally records the counts in the active request budget.
"""

from __future__ import annotations

from typing import Any

import httpx

from agents.chap12.budget import CURRENT
from models.errors import DependencyUnavailable
from models.providers import OllamaStructuredModel


def output_budget(prompt: str) -> int:
    """The Project 1 adapter's per-prompt num_predict selection, plus the round 7 KIND."""
    if prompt.startswith("KIND: CONTROLLED_ANSWER\n"):
        return 1200
    if prompt.startswith("KIND: FACT_AUDIT\n"):
        return 900
    if prompt.startswith("KIND: CLAIM_AUDIT\n"):
        return 512
    if prompt.startswith("KIND: ANSWERABILITY_SELECT\n"):
        return 700  # round 7: reasons (asked, rejected) precede the verdict
    return 300


class TokenMeteredOllamaModel(OllamaStructuredModel):
    def __init__(self, base_url: str, model: str, timeout: float = 120,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        super().__init__(base_url, model, timeout)
        self.transport = transport

    async def generate(self, prompt: str, schema: dict[str, Any]) -> str:
        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
                response = await client.post(
                    self.base_url.rstrip("/") + "/api/chat",
                    json={
                        "model": self.model, "stream": False, "format": schema,
                        "messages": [{"role": "user", "content": prompt}],
                        "options": {"temperature": 0, "num_predict": output_budget(prompt),
                                    "num_ctx": 8192},
                    },
                )
                response.raise_for_status()
                body = response.json()
                active = CURRENT.get()
                if active is not None:
                    active[0].record_tokens(body.get("prompt_eval_count"),
                                            body.get("eval_count"))
                if body.get("done_reason") == "length":
                    raise ValueError("Structured generation exceeded its token budget")
                content = body["message"]["content"]
                if not isinstance(content, str):
                    raise ValueError("model content must be a string")
                return content
        except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
            raise DependencyUnavailable("Ollama structured generation failed") from exc
