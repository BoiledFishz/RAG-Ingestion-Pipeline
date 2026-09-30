"""Native Ollama JSON-schema generation and compatible embedding providers."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Protocol

import httpx

from models.errors import DependencyUnavailable


class Embedder(Protocol):
    @property
    def identity(self) -> str: ...

    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class StructuredModel(Protocol):
    async def generate(self, prompt: str, schema: dict[str, Any]) -> str: ...


class HashEmbedder:
    """Same 384-dimensional algorithm as the preceding Pipeline; NOT semantic."""

    identity = "hash-sha256-384-v1"

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * 384
            for token in re.findall(r"[a-z0-9][a-z0-9_.:/-]*|[\u4e00-\u9fff]", text.lower()):
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                index = int.from_bytes(digest[:4], "big") % 384
                vector[index] += 1.0 if digest[4] & 1 else -1.0
            norm = math.sqrt(sum(value * value for value in vector))
            vectors.append([v / norm for v in vector] if norm else vector)
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed_documents([text]))[0]


class OllamaEmbedder:
    def __init__(self, base_url: str, model: str, timeout: float = 120) -> None:
        self.base_url, self.model, self.timeout = base_url, model, timeout

    @property
    def identity(self) -> str:
        return f"ollama:{self.model}"

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url.rstrip("/") + "/api/embed",
                    json={"model": self.model, "input": texts},
                )
                response.raise_for_status()
                vectors = response.json().get("embeddings")
                if not isinstance(vectors, list) or len(vectors) != len(texts):
                    raise ValueError("invalid embedding batch")
                result = [[float(v) for v in vector] for vector in vectors]
                if not all(vector and all(math.isfinite(v) for v in vector) for vector in result):
                    raise ValueError("invalid embedding values")
                return result
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise DependencyUnavailable("Ollama embedding request failed") from exc

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed_documents([text]))[0]


class OllamaStructuredModel:
    def __init__(self, base_url: str, model: str, timeout: float = 120) -> None:
        self.base_url, self.model, self.timeout = base_url, model, timeout

    async def generate(self, prompt: str, schema: dict[str, Any]) -> str:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url.rstrip("/") + "/api/chat",
                    json={
                        "model": self.model,
                        "stream": False,
                        "format": schema,
                        "messages": [{"role": "user", "content": prompt}],
                        "options": {"temperature": 0, "num_predict": 1500},
                    },
                )
                response.raise_for_status()
                content = response.json()["message"]["content"]
                if not isinstance(content, str):
                    raise ValueError("model content must be a string")
                return content
        except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
            raise DependencyUnavailable("Ollama structured generation failed") from exc
