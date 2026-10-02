from __future__ import annotations

import bz2
import json

from rag.techqa.data import documents

from vectorstore.techqa import (
    ChunkingConfig,
    batched,
    chunk_technote,
    iter_full_documents,
    iter_mapping_documents,
)


def test_streams_official_mapping_schema(tmp_path) -> None:
    doc = next(documents("fixture"))
    source = tmp_path / "technotes.json"
    source.write_text(json.dumps({doc["id"]: doc}), encoding="utf-8")
    rows = list(iter_mapping_documents(source))
    assert rows[0]["id"] == doc["id"]
    chunks = list(chunk_technote(rows[0], ChunkingConfig(180, 20)))
    assert len(chunks) > 1
    assert all(c.metadata["document_type"] == "ibm_technote" for c in chunks)
    assert all(c.source_file == f"techqa://{doc['id']}" for c in chunks)


def test_streams_every_bzip2_row_and_batches(tmp_path) -> None:
    docs = list(documents("fixture"))[:3]
    source = tmp_path / "full.txt.bz2"
    with bz2.open(source, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps(docs[:2]) + "\n")
        handle.write(json.dumps(docs[2:]) + "\n")
    rows = list(iter_full_documents(source))
    assert [row["id"] for row in rows] == [doc["id"] for doc in docs]
    assert [len(group) for group in batched(iter(range(5)), 2)] == [2, 2, 1]
