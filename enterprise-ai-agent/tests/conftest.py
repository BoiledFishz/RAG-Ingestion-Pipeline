from __future__ import annotations

import asyncio
import sys
from collections.abc import Iterator
from pathlib import Path

# Also allows the parent Pipeline's recursive pytest collection to run this suite.
AGENT_ROOT = Path(__file__).resolve().parents[1]
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

import pytest  # noqa: E402

from agents.rag_agent.factory import build_agent  # noqa: E402
from agents.rag_agent.service import RAGAgent  # noqa: E402
from models.providers import HashEmbedder  # noqa: E402
from models.schemas import Document  # noqa: E402
from models.settings import Settings  # noqa: E402
from vectorstore.qdrant import QdrantStore  # noqa: E402


def techqa_fixture() -> list[Document]:
    """Original official TechQA text with auditable source hashes."""
    from rag.techqa.data import documents

    from vectorstore.techqa import ChunkingConfig, chunk_technote

    return [
        chunk
        for doc in documents("fixture")
        if doc["id"] == "swg21996508"
        for chunk in chunk_technote(doc, ChunkingConfig())
    ]


@pytest.fixture
def agent_bundle() -> Iterator[tuple[RAGAgent, QdrantStore]]:
    store = QdrantStore("agent_test")
    asyncio.run(store.seed(techqa_fixture(), HashEmbedder()))
    yield build_agent(Settings(retrieval_backend="legacy"), store), store
    asyncio.run(store.close())
