from __future__ import annotations

from rag.ingestion.vector_store import VectorRecord
from rag.retrieval.contracts import SearchResult
from rag.retrieval_eval import (
    GoldenRow,
    _build_reference_chunk_index,
    _contains_expected_chunk,
)


def test_relevance_is_scored_by_evidence_chunk_not_source_file() -> None:
    row = GoldenRow(
        identifier="SEM-01",
        category="semantic",
        answerable=True,
        question="How is the object restored?",
        expected_sources=("s3.md",),
        reference_evidence=("Delete the delete marker by specifying its version ID.",),
        filters={},
    )
    records = [
        VectorRecord(
            text="Delete the delete marker by specifying its version ID.",
            metadata={
                "chunk_id": "relevant",
                "chunk_hash": "relevant",
                "source_file": "s3.md",
            },
        ),
        VectorRecord(
            text="Unrelated lifecycle policy guidance.",
            metadata={
                "chunk_id": "wrong-page",
                "chunk_hash": "wrong-page",
                "source_file": "s3.md",
            },
        ),
    ]

    reference_index = _build_reference_chunk_index([row], records)
    wrong_result = SearchResult(
        "Unrelated lifecycle policy guidance.",
        records[1].metadata,
        0.9,
        "dense",
    )

    assert reference_index[row.identifier] == frozenset({"relevant"})
    assert not _contains_expected_chunk(row, wrong_result, reference_index)
