"""No import-time clients; independent database and environment namespace."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field

from models.schemas import StrictModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(StrictModel):
    retrieval_backend: Literal["techqa", "legacy"] = "techqa"
    profile: Literal["offline", "ollama"] = "offline"
    embedding_provider: Literal["auto", "hash", "ollama"] = "auto"
    qdrant_path: Path = PROJECT_ROOT / ".agent_data" / "qdrant"
    qdrant_url: str | None = None
    qdrant_api_key: str | None = Field(default=None, repr=False)
    collection: str = "techqa_hash"
    ollama_url: str = "http://localhost:11434"
    model: str = "llama3.2:3b"
    embedding_model: str = "nomic-embed-text"
    top_k: int = Field(default=8, ge=1, le=30)
    max_context_tokens: int = Field(default=900, ge=64, le=8000)
    max_sources: int = Field(default=4, ge=1, le=4)
    min_relevance: float = Field(default=0.20, ge=0, le=1)
    tool_timeout: float = Field(default=30, gt=0, le=300)
    llm_timeout: float = Field(default=120, gt=0, le=600)

    @classmethod
    def from_env(cls) -> Settings:
        profile = os.getenv("AGENT_PROFILE", "offline")
        embedding_provider = os.getenv("AGENT_EMBEDDING_PROVIDER", "auto")
        path = Path(os.getenv("AGENT_QDRANT_PATH", ".agent_data/qdrant"))
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return cls.model_validate(
            {
                "retrieval_backend": os.getenv("AGENT_RETRIEVAL_BACKEND", "techqa"),
                "profile": profile,
                "embedding_provider": embedding_provider,
                "qdrant_path": path,
                "qdrant_url": os.getenv("AGENT_QDRANT_URL") or None,
                "qdrant_api_key": os.getenv("AGENT_QDRANT_API_KEY") or None,
                "collection": os.getenv(
                    "AGENT_COLLECTION",
                    "techqa_hash" if profile == "offline" else "techqa_ollama",
                ),
                "ollama_url": os.getenv("AGENT_OLLAMA_URL", "http://localhost:11434"),
                "model": os.getenv("AGENT_MODEL", "llama3.2:3b"),
                "embedding_model": os.getenv("AGENT_EMBEDDING_MODEL", "nomic-embed-text"),
                "top_k": int(os.getenv("AGENT_TOP_K", "8")),
                "max_context_tokens": int(os.getenv("AGENT_MAX_CONTEXT_TOKENS", "900")),
                "max_sources": int(os.getenv("AGENT_MAX_SOURCES", "4")),
                "min_relevance": float(os.getenv("AGENT_MIN_RELEVANCE", "0.20")),
                "tool_timeout": float(os.getenv("AGENT_TOOL_TIMEOUT", "30")),
                "llm_timeout": float(os.getenv("AGENT_LLM_TIMEOUT", "120")),
            }
        )
