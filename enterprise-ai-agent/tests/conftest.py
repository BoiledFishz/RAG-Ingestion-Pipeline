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
    """Small TechQA-shaped fixture; production never reads this fixture."""
    return [
        Document(
            chunk_id="techqa:swg-test-streams:0",
            source_file="techqa://swg-test-streams",
            text=(
                "IBM Streams environment variables may be set directly on the instance with "
                "streamtool setproperty --application-ev after an upgrade."
            ),
            metadata={
                "status": "published",
                "language": "en",
                "document_type": "ibm_technote",
                "techqa_document_id": "swg-test-streams",
            },
        ),
        Document(
            chunk_id="techqa:swg-test-websphere:0",
            source_file="techqa://swg-test-websphere",
            text=(
                "WebSphere ADMU0111E indicates the server process could not be started. "
                "Review the server logs and verify the configured Java process settings."
            ),
            metadata={
                "status": "published",
                "language": "en",
                "document_type": "ibm_technote",
                "techqa_document_id": "swg-test-websphere",
            },
        ),
    ]


@pytest.fixture
def agent_bundle() -> Iterator[tuple[RAGAgent, QdrantStore]]:
    store = QdrantStore("agent_test")
    asyncio.run(store.seed(techqa_fixture(), HashEmbedder()))
    yield build_agent(Settings(), store), store
    asyncio.run(store.close())
