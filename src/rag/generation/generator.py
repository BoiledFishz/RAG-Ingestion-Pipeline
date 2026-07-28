"""Grounded answer generation through a local Ollama endpoint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from rag.generation.prompts import ANSWER_PROMPT


class AnswerGenerator(Protocol):
    async def generate(
        self,
        *,
        question: str,
        context: str,
        correction: str | None = None,
    ) -> str:
        """Generate one grounded answer."""


@dataclass(slots=True)
class OllamaGenerator:
    model: str = "llama3.2:3b"
    base_url: str = "http://localhost:11434"
    timeout_seconds: float = 120.0

    async def generate(
        self,
        *,
        question: str,
        context: str,
        correction: str | None = None,
    ) -> str:
        async with httpx.AsyncClient(
            base_url=self.base_url.rstrip("/"), timeout=self.timeout_seconds
        ) as client:
            response = await client.post(
                "/api/generate",
                json={
                    "model": self.model,
                    "stream": False,
                    "options": {"temperature": 0},
                    "prompt": ANSWER_PROMPT.format(
                        question=question,
                        context=context,
                        correction=correction or "None.",
                    ),
                },
            )
            response.raise_for_status()
            return str(response.json().get("response", "")).strip()
