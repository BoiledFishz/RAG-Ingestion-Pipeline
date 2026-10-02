"""Regression checks using only the traceable official TechQA fixture."""

from __future__ import annotations

import asyncio
import json

from rag.retrieval.fusion import reciprocal_rank_fusion
from rag.techqa.data import FIXTURE_ROOT, digest, documents
from rag.techqa.index import TechQAIndex, build
from rag.techqa.retrieval import FullSparseRetriever, legacy_chunks


def test_official_fixture_hashes_and_no_question_answers_in_documents():
    manifest = json.loads((FIXTURE_ROOT / "manifest.json").read_text())
    rows = list(documents("fixture"))
    assert len(rows) == manifest["documents"] == 41
    assert all(digest(row["text"]) == manifest["content_hashes"][row["id"]] for row in rows)
    assert all("ANSWER" not in row and "QUESTION_ID" not in row for row in rows)


def test_disk_bm25_metadata_filter_and_chunk_identity(tmp_path):
    path = tmp_path / "official.sqlite"
    first = build(path, "fixture")
    assert build(path, "fixture") == first
    index = TechQAIndex(path)
    retriever = FullSparseRetriever(index)
    query = "Streams 4.1.1.2 environment variables bashrc"
    result = asyncio.run(retriever.retrieve(query, limit=5, filters={"status": "draft"}))
    assert result[0].metadata["techqa_document_id"] == "swg21996508"
    assert all(r.status == "published" for r in result)
    original = index.get("swg21996508")
    assert result[0].chunk_id in {r.chunk_id for r in legacy_chunks(original)}
    assert asyncio.run(retriever.retrieve(query, filters={"language": "zh-CN"})) == []
    assert asyncio.run(retriever.retrieve(query, filters={"source_file": "techqa://missing"})) == []


def test_rrf_preserves_sparse_metadata_for_shared_chunk():
    from dataclasses import replace

    chunk = legacy_chunks(next(documents("fixture")))[0]
    dense = replace(chunk, backend="dense", metadata={**chunk.metadata, "dense_marker": True})
    sparse = replace(chunk, metadata={**chunk.metadata, "bm25_document_rank": 1})
    result = reciprocal_rank_fusion([[dense], [sparse]])
    assert len(result) == 1
    assert result[0].metadata["bm25_document_rank"] == 1
    assert result[0].metadata["dense_marker"]


def test_training_thresholds_reproduce_from_recorded_official_run():
    from rag.techqa.calibrate import calibrate
    from rag.techqa.data import ROOT

    recorded = json.loads((ROOT / "config/techqa_thresholds.json").read_text())
    assert calibrate(ROOT / "evals/techqa_calibration") == recorded


def test_calibration_rejects_dev_labels():
    import pytest

    from rag.techqa.calibrate import calibrate
    from rag.techqa.data import ROOT

    with pytest.raises(ValueError, match="training questions"):
        calibrate(ROOT / "evals/techqa_full")
