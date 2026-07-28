from __future__ import annotations

from rag.retrieval.context_builder import ContextBuilder
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
