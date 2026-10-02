from __future__ import annotations

import asyncio

from rag.ingestion.models import Chunk
from rag.ingestion.providers import HashEmbeddingProvider
from rag.ingestion.vector_store import QdrantVectorStore
from rag.retrieval.dense import DenseRetriever
from rag.techqa.data import questions


def test_dense_retriever_returns_persisted_metadata() -> None:
    async def scenario() -> None:
        store = QdrantVectorStore(path=None, collection_name="dense_test")
        embedder = HashEmbeddingProvider(dimensions=64)
        chunk = Chunk(
            text=questions("fixture")[0]["ANSWER"],
            metadata={
                "source_file": "techqa://swg21996508",
                "page_number": 1,
                "chunk_hash": "hash-1",
                "chunk_id": "hash-1",
                "status": "published",
            },
        )
        vectors = await embedder.embed_documents([chunk.text])
        await store.ensure_collection(len(vectors[0]))
        await store.upsert([chunk], vectors)
        results = await DenseRetriever(embedder=embedder, store=store).retrieve(
            "Streams environment variables", limit=1
        )
        assert results[0].metadata["source_file"] == "techqa://swg21996508"
        assert results[0].source_file == "techqa://swg21996508"
        assert results[0].page_number == 1
        assert results[0].chunk_hash == "hash-1"
        assert results[0].chunk_id == "hash-1"
        assert results[0].retrieval_rank == 1
        assert results[0].retrieval_score is not None
        serialized = results[0].to_dict()
        assert serialized["source_file"] == "techqa://swg21996508"
        assert serialized["page_number"] == 1
        assert serialized["retrieval_rank"] == 1

    asyncio.run(scenario())
