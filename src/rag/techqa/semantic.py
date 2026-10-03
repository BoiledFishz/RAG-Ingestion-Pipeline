"""Complete, resumable semantic encoding of every official TechQA chunk.

MiniLM windows are pooled so no input is silently discarded at its token limit.
Source/chunk identities stay identical to sparse retrieval. Index publication is
atomic and happens only after every source document and stored vector is checked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sqlite3
import time
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path
from threading import Lock
from typing import Any

from rag.techqa.data import ARCHIVE_SHA256, INDEX_PATH, ROOT
from rag.techqa.retrieval import legacy_chunks

LOGGER = logging.getLogger(__name__)
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MODEL_PATH = ROOT / ".rag_data/models/minilm"
SEMANTIC_ROOT = ROOT / ".rag_data/techqa_semantic"


def read_manifest(path: Path) -> dict[str, Any]:
    value: dict[str, Any] = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("encoder"), dict):
        raise ValueError("Incomplete or incompatible semantic index manifest")
    provenance = value.get("encoder", {})
    expected_identity = hashlib.sha256(json.dumps(provenance, sort_keys=True).encode()).hexdigest()
    if (value.get("complete") is not True or value.get("dimension") != 384
            or value.get("scope") not in {"fixture", "core", "full"}
            or value.get("source_archive_sha256") != ARCHIVE_SHA256
            or provenance.get("model") != MODEL_ID
            or provenance.get("revision") != MODEL_REVISION
            or provenance.get("pooling") != "window256-stride16-mean-v1"
            or value.get("embedding_id") != expected_identity
            or not isinstance(value.get("chunks"), int) or value["chunks"] <= 0
            or not isinstance(value.get("documents"), int) or value["documents"] <= 0):
        raise ValueError("Incomplete or incompatible semantic index manifest")
    return value


def download_model(path: Path = MODEL_PATH) -> None:
    from huggingface_hub import snapshot_download

    path.mkdir(parents=True, exist_ok=True)
    revision = MODEL_REVISION
    snapshot_download(
        MODEL_ID,
        revision=revision,
        local_dir=path,
        allow_patterns=[
            "config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json",
            "vocab.txt", "special_tokens_map.json", "README.md",
        ],
    )
    manifest = {"model": MODEL_ID, "revision": revision, "pooling": "window256-stride16-mean-v1"}
    (path / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Downloaded pinned MiniLM model %s", revision)


class MiniLMEncoder:
    def __init__(self, path: Path = MODEL_PATH, batch_size: int = 128,
                 device: str | None = None) -> None:
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.torch = torch
        self.provenance = json.loads((path / "provenance.json").read_text(encoding="utf-8"))
        if (self.provenance.get("model") != MODEL_ID
                or self.provenance.get("revision") != MODEL_REVISION
                or self.provenance.get("pooling") != "window256-stride16-mean-v1"):
            raise ValueError("Encoder provenance does not match the pinned semantic model")
        self.identity = hashlib.sha256(
            json.dumps(self.provenance, sort_keys=True).encode()
        ).hexdigest()
        self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        if self.device not in {"cuda", "cpu"}:
            raise ValueError("Semantic device must be cuda or cpu")
        torch.set_num_threads(4)
        self.model = AutoModel.from_pretrained(
            path, local_files_only=True, use_safetensors=True, attn_implementation="sdpa"
        ).eval().to(self.device)
        if self.device == "cuda":
            self.model = self.model.half()
        self.batch_size = batch_size
        self.lock = Lock()
        LOGGER.info("MiniLM device=%s identity=%s", self.device, self.identity)

    def encode(self, texts: Sequence[str]) -> Any:
        import numpy as np

        if not texts:
            return np.empty((0, 384), dtype="float32")
        with self.lock, self.torch.inference_mode():
            encoded = self.tokenizer(
                list(texts), truncation=True, max_length=256, stride=16,
                return_overflowing_tokens=True, padding=False,
            )
            owners = encoded.pop("overflow_to_sample_mapping")
            sums = np.zeros((len(texts), 384), dtype="float32")
            weights = np.zeros(len(texts), dtype="float32")
            cursor = 0
            while cursor < len(owners):
                count = min(self.batch_size, len(owners) - cursor)
                rows = [
                    {name: values[i] for name, values in encoded.items()}
                    for i in range(cursor, cursor + count)
                ]
                batch = self.tokenizer.pad(rows, padding=True, return_tensors="pt")
                batch = {k: v.to(self.device) for k, v in batch.items()}
                try:
                    states = self.model(**batch).last_hidden_state.float()
                    mask = batch["attention_mask"].unsqueeze(-1).float()
                    pooled = (states * mask).sum(1) / mask.sum(1).clamp(min=1)
                    pooled = self.torch.nn.functional.normalize(pooled, p=2, dim=1)
                    vectors = pooled.cpu().numpy()
                except self.torch.cuda.OutOfMemoryError:
                    if count <= 1:
                        raise
                    self.batch_size = max(1, count // 2)
                    self.torch.cuda.empty_cache()
                    LOGGER.warning("Reducing MiniLM batch size to %d", self.batch_size)
                    continue
                for offset, vector in enumerate(vectors):
                    owner = owners[cursor + offset]
                    weight = max(1, len(rows[offset]["input_ids"]) - 2)
                    sums[owner] += vector * weight
                    weights[owner] += weight
                cursor += count
            sums /= weights[:, None]
            norms = np.linalg.norm(sums, axis=1, keepdims=True)
            if not np.isfinite(sums).all() or (norms <= 0).any():
                raise ValueError("MiniLM produced invalid/zero semantic vectors")
            return np.ascontiguousarray(sums / norms, dtype="float32")


def build(
    source: Path = INDEX_PATH, destination: Path = SEMANTIC_ROOT,
    *, model_path: Path = MODEL_PATH, document_batch: int = 64,
) -> dict[str, Any]:
    from rag.techqa.index import TechQAIndex

    index = TechQAIndex(source)
    if (destination / "manifest.json").is_file():
        manifest = read_manifest(destination)
        if (manifest.get("source_index") != str(source.resolve())
                or manifest["scope"] != index.manifest["scope"]
                or manifest["documents"] != int(index.manifest["document_count"])):
            raise ValueError("Completed semantic index source differs; use another destination")
        vector_path = destination / "index.faiss"
        minimum_bytes = manifest["chunks"] * manifest["dimension"] * 4
        if not vector_path.is_file() or vector_path.stat().st_size < minimum_bytes:
            raise ValueError("Completed semantic vector file is missing or truncated")
        metadata_path = destination / "chunks.sqlite"
        uri = metadata_path.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as db:
            count = db.execute("SELECT count(*) FROM chunks").fetchone()[0]
            state = dict(db.execute("SELECT key,value FROM state"))
        if (count != manifest["chunks"] or state.get("embedding_id") != manifest["embedding_id"]
                or state.get("source") != str(source.resolve())
                or int(state.get("documents_completed", "0")) != manifest["documents"]):
            raise ValueError("Completed semantic metadata/state differs from its manifest")
        LOGGER.info("Reusing complete semantic index without loading/rebuilding vectors: %s",
                    manifest)
        return manifest

    import faiss
    import numpy as np

    destination.mkdir(parents=True, exist_ok=True)
    encoder = MiniLMEncoder(model_path)
    database = destination / "chunks.sqlite"
    started = time.perf_counter()
    with closing(sqlite3.connect(database)) as db, index.connect() as original:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS chunks (
                rowid INTEGER PRIMARY KEY, chunk_id TEXT UNIQUE, doc_id TEXT,
                text TEXT, metadata TEXT, vector BLOB);
            CREATE INDEX IF NOT EXISTS chunks_doc ON chunks(doc_id);
            CREATE TABLE IF NOT EXISTS embeddings (hash TEXT PRIMARY KEY, vector BLOB);
            CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT);
        """)
        state = dict(db.execute("SELECT key,value FROM state"))
        identity = {"embedding_id": encoder.identity, "source": str(source.resolve())}
        if state and any(state.get(k) != v for k, v in identity.items()):
            raise ValueError("Resume model/source identity mismatch; use another destination")
        db.executemany("INSERT OR IGNORE INTO state VALUES (?,?)", identity.items())
        db.commit()
        last = int(state.get("last_document_rowid", "0"))
        completed = int(state.get("documents_completed", "0"))
        while True:
            rows = original.execute(
                "SELECT rowid,doc_id,title,text,metadata FROM docs WHERE rowid>? "
                "ORDER BY rowid LIMIT ?", (last, document_batch),
            ).fetchall()
            if not rows:
                break
            chunks = [
                c for row in rows
                for c in legacy_chunks(TechQAIndex._document(row[1:]))
            ]
            cached = {}
            for chunk in chunks:
                found = db.execute(
                    "SELECT vector FROM embeddings WHERE hash=?", (chunk.chunk_hash,)
                ).fetchone()
                if found:
                    cached[chunk.chunk_hash] = found[0]
            missing = {c.chunk_hash: c.text for c in chunks if c.chunk_hash not in cached}
            keys = list(missing)
            for offset in range(0, len(keys), 256):
                group = keys[offset:offset + 256]
                vectors = encoder.encode([missing[key] for key in group])
                items = [(key, vector.tobytes())
                         for key, vector in zip(group, vectors, strict=True)]
                db.executemany("INSERT OR IGNORE INTO embeddings VALUES (?,?)", items)
                db.commit()  # A crash never causes already-computed vectors to be billed twice.
                cached.update(items)
            db.executemany(
                "INSERT OR IGNORE INTO chunks(chunk_id,doc_id,text,metadata,vector) "
                "VALUES (?,?,?,?,?)",
                [
                    (c.chunk_id, c.metadata["techqa_document_id"], c.text,
                     json.dumps({**c.metadata, "_embedding_id": encoder.identity}),
                     cached[c.chunk_hash])
                    for c in chunks
                ],
            )
            last, completed = rows[-1][0], completed + len(rows)
            db.executemany("INSERT OR REPLACE INTO state VALUES (?,?)", [
                ("last_document_rowid", str(last)), ("documents_completed", str(completed)),
            ])
            db.commit()
            if completed % 1024 < document_batch:
                LOGGER.info("Semantic progress documents=%d/%s elapsed=%.1fs", completed,
                            index.manifest["document_count"], time.perf_counter() - started)
        expected = int(index.manifest["document_count"])
        actual_docs = db.execute("SELECT count(DISTINCT doc_id) FROM chunks").fetchone()[0]
        if actual_docs != expected or completed != expected:
            raise ValueError(f"Semantic coverage incomplete: {actual_docs}/{expected}")
        LOGGER.info("All %d documents encoded; building exact semantic search", expected)
        faiss.omp_set_num_threads(4)
        dense = faiss.IndexFlatIP(384)
        cursor = db.execute("SELECT rowid,vector FROM chunks ORDER BY rowid")
        expected_row = 1
        while rows := cursor.fetchmany(8192):
            if any(row[0] != expected_row + i for i, row in enumerate(rows)):
                raise ValueError("Semantic row IDs are not contiguous")
            matrix = np.vstack([np.frombuffer(row[1], dtype="float32") for row in rows])
            if not np.isfinite(matrix).all():
                raise ValueError("Stored vectors contain non-finite values")
            dense.add(matrix)
            expected_row += len(rows)
        temporary = destination / "index.faiss.partial"
        faiss.write_index(dense, str(temporary))
        os.replace(temporary, destination / "index.faiss")
        manifest = {
            "complete": True, "scope": index.manifest["scope"],
            "source_archive_sha256": ARCHIVE_SHA256,
            "documents": actual_docs, "chunks": dense.ntotal, "dimension": 384,
            "embedding_id": encoder.identity, "encoder": encoder.provenance,
            "search": "Faiss IndexFlatIP, exact cosine over unit vectors",
            "source_index": str(source.resolve()),
        }
        temporary_manifest = destination / "manifest.json.partial"
        temporary_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary_manifest, destination / "manifest.json")
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    LOGGER.info("Published complete semantic index: %s", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-model", action="store_true")
    parser.add_argument("--source", type=Path, default=INDEX_PATH)
    parser.add_argument("--destination", type=Path, default=SEMANTIC_ROOT)
    args = parser.parse_args()
    if args.download_model:
        download_model()
    else:
        build(args.source, args.destination)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
