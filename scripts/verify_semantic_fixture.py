"""Integration check using the pinned encoder and original committed TechQA text."""

from __future__ import annotations

import logging

from rag.techqa.data import ROOT, documents, question_text, questions
from rag.techqa.embedding_server import SearchRequest, SemanticSearch
from rag.techqa.index import build as build_source
from rag.techqa.retrieval import legacy_chunks
from rag.techqa.semantic import build

LOGGER = logging.getLogger(__name__)


def main() -> None:
    destination = ROOT / ".rag_data/semantic_fixture"
    source = ROOT / ".rag_data/semantic_fixture_source.sqlite"
    build_source(source, "fixture")
    first = build(source, destination)
    assert first == build(source, destination)  # No duplicate vectors on repeat.
    engine = SemanticSearch(destination)
    question = questions("fixture")[0]
    results = engine.search(SearchRequest(query=question_text(question), limit=5))
    assert results[0]["metadata"]["techqa_document_id"] == question["DOCUMENT"]
    original = next(d for d in documents("fixture") if d["id"] == question["DOCUMENT"])
    source_ids = {c.chunk_id for c in legacy_chunks(original)}
    scoped = engine.search(SearchRequest(query=question_text(question), filters={
        "source_file": f"techqa://{question['DOCUMENT']}", "status": "draft",
    }))
    assert scoped and all(r["metadata"]["status"] == "published" for r in scoped)
    assert all(r["metadata"]["chunk_id"] in source_ids for r in scoped)
    assert engine.search(SearchRequest(
        query=question_text(question), filters={"language": "zh-CN"},
    )) == []
    LOGGER.info("Pinned CUDA semantic integration passed: %d official documents, %d chunks",
                first["documents"], first["chunks"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
