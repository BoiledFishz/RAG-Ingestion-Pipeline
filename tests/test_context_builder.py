from __future__ import annotations

import asyncio

from rag.retrieval.context_builder import ContextBuilder, count_tokens
from rag.retrieval.contracts import SearchResult


def test_context_builder_deduplicates_and_includes_citation() -> None:
    metadata = {
        "chunk_hash": "same",
        "source_file": "guide.pdf",
        "page_number": 7,
        "context_summary": "This chunk explains S3 permissions.",
    }
    result = SearchResult("Check the bucket policy.", metadata, 1.0, "hybrid")
    context = ContextBuilder().build([result, result])
    assert context.count("Check the bucket policy") == 1
    assert "guide.pdf, page: 7" in context
    assert "[S1]" in context
    assert "<retrieved_context>" in context


def test_context_token_budget() -> None:
    results = [
        SearchResult(
            text="word " * 100,
            metadata={
                "chunk_hash": f"hash-{index}",
                "chunk_id": f"chunk-{index}",
                "source_file": f"guide-{index}.pdf",
                "page_number": index,
            },
            score=1.0,
            backend="dense",
        )
        for index in range(5)
    ]
    built = ContextBuilder(
        max_context_tokens=80,
        max_chunks_per_document=2,
    ).build_context(results)
    assert built.context
    assert built.token_count <= 80
    assert count_tokens(built.context) <= 80


class ParentResolver:
    async def retrieve_by_chunk_ids(self, chunk_ids: list[str]) -> list[SearchResult]:
        assert chunk_ids == ["parent-1"]
        return [
            SearchResult(
                "Expanded parent troubleshooting procedure.",
                {
                    "chunk_id": "parent-1",
                    "chunk_hash": "parent-hash",
                    "source_file": "guide.pdf",
                    "page_number": 4,
                },
                0.0,
                "parent",
            )
        ]


def test_parent_is_fetched_after_final_selection() -> None:
    child = SearchResult(
        "short child",
        {
            "chunk_id": "child-1",
            "chunk_hash": "child-hash",
            "parent_id": "parent-1",
            "source_file": "guide.pdf",
            "page_number": 4,
        },
        0.9,
        "hybrid",
    )
    built = asyncio.run(
        ContextBuilder(max_context_tokens=100).build_with_parents(
            [child],
            parent_resolver=ParentResolver(),
        )
    )
    assert "Expanded parent troubleshooting procedure." in built.context
    assert built.source_map["S1"].chunk_id == "parent-1"
