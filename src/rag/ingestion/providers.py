"""Async LLM summarization and embedding providers."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import re
from dataclasses import dataclass
from typing import Protocol

import httpx

from rag.generation.prompts import CONTEXT_SUMMARY_PROMPT

LOGGER = logging.getLogger(__name__)


class SummaryProvider(Protocol):
    async def summarize(self, text: str) -> str:
        """Return exactly one sentence describing a chunk's local context."""


class EmbeddingProvider(Protocol):
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed documents while preserving input order."""

    async def embed_query(self, text: str) -> list[float]:
        """Embed one search query."""


def _first_sentence(text: str, *, max_chars: int = 240) -> str:
    value = re.sub(r"\s+", " ", text).strip().strip("\"'`- ")
    if not value:
        return "This chunk contains no usable textual context."
    match = re.search(r"[.!?。！？]", value)
    if match:
        value = value[: match.end()]
    else:
        value = value[:max_chars].rstrip(" ,;:，；：") + "."
    return value[:max_chars].strip()


@dataclass(slots=True)
class ExtractiveSummaryProvider:
    """Deterministic fallback used when the configured LLM is unavailable."""

    max_chars: int = 240

    async def summarize(self, text: str) -> str:
        return _first_sentence(text, max_chars=self.max_chars)


@dataclass(slots=True)
class OllamaSummaryProvider:
    """Generate one-sentence context summaries through Ollama's free local API."""

    model: str = "llama3.2:3b"
    base_url: str = "http://localhost:11434"
    timeout_seconds: float = 60.0
    max_retries: int = 2

    async def summarize(self, text: str) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "options": {"temperature": 0, "num_predict": 80},
            "prompt": CONTEXT_SUMMARY_PROMPT.format(chunk=text),
        }
        response_data = await self._post_with_retry("/api/generate", payload)
        return _first_sentence(str(response_data.get("response", "")))

    async def _post_with_retry(
        self, endpoint: str, payload: dict[str, object]
    ) -> dict[str, object]:
        error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    base_url=self.base_url.rstrip("/"), timeout=self.timeout_seconds
                ) as client:
                    response = await client.post(endpoint, json=payload)
                    response.raise_for_status()
                    result = response.json()
                    if not isinstance(result, dict):
                        raise ValueError("Ollama returned a non-object response")
                    return result
            except (httpx.HTTPError, ValueError) as exc:
                error = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(2**attempt)
        raise RuntimeError(f"Ollama request failed after retries: {error}") from error


@dataclass(slots=True)
class OllamaEmbeddingProvider:
    """Batch embeddings via Ollama; requests are asynchronous and bounded."""

    model: str = "nomic-embed-text"
    base_url: str = "http://localhost:11434"
    batch_size: int = 32
    concurrency: int = 4
    timeout_seconds: float = 120.0

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        semaphore = asyncio.Semaphore(self.concurrency)

        async def embed_batch(batch: list[str]) -> list[list[float]]:
            async with semaphore:
                async with httpx.AsyncClient(
                    base_url=self.base_url.rstrip("/"), timeout=self.timeout_seconds
                ) as client:
                    response = await client.post(
                        "/api/embed", json={"model": self.model, "input": batch}
                    )
                    response.raise_for_status()
                    data = response.json()
                    vectors = data.get("embeddings")
                    if not isinstance(vectors, list) or len(vectors) != len(batch):
                        raise ValueError("Ollama returned an invalid embedding batch")
                    return [[float(value) for value in vector] for vector in vectors]

        batches = [
            texts[index : index + self.batch_size]
            for index in range(0, len(texts), self.batch_size)
        ]
        nested = await asyncio.gather(*(embed_batch(batch) for batch in batches))
        return [vector for batch in nested for vector in batch]

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_documents([text])
        return vectors[0]


@dataclass(slots=True)
class HashEmbeddingProvider:
    """Offline feature-hashing embeddings for tests and zero-dependency demos.

    This provider is deterministic but not a replacement for a semantic production
    embedding model. It keeps CI and the included benchmark reproducible.
    """

    dimensions: int = 384

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[a-z0-9][a-z0-9_.:/-]*|[\u4e00-\u9fff]", text.lower())

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in self._tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed(text)
