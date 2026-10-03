"""Control-plane checks need no model download, GPU or generated test corpus."""

import hashlib
import json
import sqlite3

import pytest

from rag.techqa.data import ARCHIVE_SHA256
from rag.techqa.embedding_server import metadata_connection
from rag.techqa.semantic import MODEL_ID, MODEL_REVISION, read_manifest


def manifest():
    encoder = {"model": MODEL_ID, "revision": MODEL_REVISION,
               "pooling": "window256-stride16-mean-v1"}
    return {
        "complete": True, "scope": "fixture", "documents": 41, "chunks": 176,
        "dimension": 384, "source_archive_sha256": ARCHIVE_SHA256, "encoder": encoder,
        "embedding_id": hashlib.sha256(json.dumps(encoder, sort_keys=True).encode()).hexdigest(),
    }


@pytest.mark.parametrize("key,value", [
    ("complete", False), ("dimension", 768), ("embedding_id", "hash-sha256-384-v1"),
    ("source_archive_sha256", "invalid"), ("documents", 0),
    ("encoder", None), ("scope", "unknown"),
])
def test_incomplete_or_incompatible_semantic_index_is_rejected(tmp_path, key, value):
    data = manifest()
    data[key] = value
    (tmp_path / "manifest.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="Incomplete or incompatible"):
        read_manifest(tmp_path)


def test_pinned_official_manifest_is_accepted_without_loading_heavy_dependencies(tmp_path):
    data = manifest()
    (tmp_path / "manifest.json").write_text(json.dumps(data), encoding="utf-8")
    assert read_manifest(tmp_path) == data


def test_serving_missing_metadata_does_not_create_empty_database(tmp_path):
    with pytest.raises(sqlite3.OperationalError):
        metadata_connection(tmp_path)
    assert not (tmp_path / "chunks.sqlite").exists()


def test_serving_metadata_is_read_only(tmp_path):
    path = tmp_path / "chunks.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE chunks (text TEXT)")
    connection = metadata_connection(tmp_path)
    try:
        assert connection.execute("SELECT count(*) FROM chunks").fetchone() == (0,)
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("INSERT INTO chunks VALUES ('')")
    finally:
        connection.close()


def test_completed_build_cannot_silently_reuse_a_missing_vector_file(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from rag.techqa import index, semantic

    source = tmp_path / "source.sqlite"
    destination = tmp_path / "semantic"
    destination.mkdir()
    data = {**manifest(), "source_index": str(source.resolve())}
    (destination / "manifest.json").write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(index, "TechQAIndex", lambda _: SimpleNamespace(
        manifest={"scope": "fixture", "document_count": "41"},
    ))

    def forbidden_encoder(*args, **kwargs):
        pytest.fail("Invalid completed artifacts must fail before loading an encoder")

    monkeypatch.setattr(semantic, "MiniLMEncoder", forbidden_encoder)
    with pytest.raises(ValueError, match="missing or truncated"):
        semantic.build(source, destination)
