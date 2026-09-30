from __future__ import annotations

import bz2
import json

from vectorstore.techqa import (
    ChunkingConfig,
    batched,
    chunk_technote,
    iter_full_documents,
    iter_mapping_documents,
)


def raw_doc(doc_id: str = "swg1") -> dict[str, object]:
    return {
        "id": doc_id,
        "title": "IBM WebSphere startup error",
        "text": "ADMU0111E means the server process could not start. " * 12,
        "metadata": {"productName": "IBM WebSphere"},
    }


def test_streams_official_mapping_schema(tmp_path) -> None:
    source = tmp_path / "technotes.json"
    source.write_text(json.dumps({"swg1": raw_doc()}), encoding="utf-8")
    rows = list(iter_mapping_documents(source))
    assert rows[0]["id"] == "swg1"
    chunks = list(chunk_technote(rows[0], ChunkingConfig(180, 20)))
    assert len(chunks) > 1
    assert all(c.metadata["document_type"] == "ibm_technote" for c in chunks)
    assert all(c.source_file == "techqa://swg1" for c in chunks)


def test_streams_every_bzip2_row_and_batches(tmp_path) -> None:
    source = tmp_path / "full.txt.bz2"
    with bz2.open(source, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps([raw_doc("a"), raw_doc("b")]) + "\n")
        handle.write(json.dumps([raw_doc("c")]) + "\n")
    rows = list(iter_full_documents(source))
    assert [row["id"] for row in rows] == ["a", "b", "c"]
    assert [len(group) for group in batched(iter(range(5)), 2)] == [2, 2, 1]
