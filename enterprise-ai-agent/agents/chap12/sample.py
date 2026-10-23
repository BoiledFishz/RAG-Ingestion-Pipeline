"""Deterministic random TechQA sample: questions plus their official candidate documents.

The sample index reuses the Project 1 TechQAIndex schema (docs + FTS5 + vocabulary + manifest)
so the existing BM25/rerank/parent pipeline runs unchanged, and adds one structured table
`technotes` derived only from official document metadata for the Database Query Worker.
QA answers, labels and gold document IDs are written to a separate scoring file, never here.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import sqlite3
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

SAMPLE_SCOPE = "chap12-sample-v1"
DEFAULT_SEED = 20261011
DEFAULT_SIZE = 150
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def doc_class(doc_id: str) -> str:
    """Document class from the official TechQA/IBM identifier prefix (not from text)."""
    if doc_id.startswith("swg1"):
        return "apar"
    if doc_id.startswith("swg27"):
        return "product_documentation"
    if doc_id.startswith("swg2"):
        return "technote"
    return "other"


def select_questions(questions: list[dict[str, Any]], size: int, seed: int) -> list[dict[str, Any]]:
    if not 100 <= size <= 200:
        raise ValueError("sample size must be between 100 and 200")
    ordered = sorted(questions, key=lambda q: str(q["QUESTION_ID"]))
    if size > len(ordered):
        raise ValueError("sample larger than source split")
    chosen = random.Random(seed).sample(ordered, size)
    return sorted(chosen, key=lambda q: str(q["QUESTION_ID"]))


def candidate_doc_ids(questions: Iterable[dict[str, Any]]) -> list[str]:
    """Union of official DOC_IDS (gold answer document plus official distractors)."""
    return sorted({str(d) for q in questions for d in q["DOC_IDS"]})


def write_index(path: Path, docs: Iterable[dict[str, Any]], manifest: dict[str, str]) -> int:
    if path.exists():
        raise FileExistsError(f"{path} exists; choose a new path to keep samples immutable")
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    try:
        # One-shot immutable build: no rollback journal file is needed or left behind.
        db.execute("PRAGMA journal_mode=MEMORY")
        db.executescript("""
            CREATE TABLE docs (
                rowid INTEGER PRIMARY KEY, doc_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL, text TEXT NOT NULL, metadata TEXT NOT NULL);
            CREATE VIRTUAL TABLE search USING fts5(
                title, text, content='docs', content_rowid='rowid', tokenize='porter unicode61');
            CREATE TABLE manifest (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE technotes (
                doc_id TEXT PRIMARY KEY, title TEXT NOT NULL,
                product_name TEXT, product_id TEXT, doc_class TEXT NOT NULL,
                published_date TEXT);
            CREATE TABLE document_products (
                doc_id TEXT NOT NULL REFERENCES technotes(doc_id), product_id TEXT NOT NULL,
                PRIMARY KEY (product_id, doc_id));
        """)
        count = 0
        for doc in docs:
            meta = doc.get("metadata") or {}
            published = str(meta.get("date") or "")
            db.execute(
                "INSERT INTO docs(doc_id,title,text,metadata) VALUES (?,?,?,?)",
                (doc["id"], doc["title"], doc["text"], json.dumps(meta)),
            )
            db.execute(
                "INSERT INTO technotes VALUES (?,?,?,?,?,?)",
                (
                    doc["id"], doc["title"],
                    str(meta.get("productName") or "").strip() or None,
                    str(meta.get("productId") or "").strip() or None,
                    doc_class(doc["id"]),
                    published if DATE.match(published) else None,
                ),
            )
            ids = {p.strip() for p in str(meta.get("productId") or "").split(",") if p.strip()}
            db.executemany("INSERT INTO document_products VALUES (?,?)",
                           [(doc["id"], product_id) for product_id in sorted(ids)])
            count += 1
        db.execute("INSERT INTO search(search) VALUES ('rebuild')")
        db.execute("CREATE VIRTUAL TABLE vocabulary USING fts5vocab(search, 'row')")
        rows = {**manifest, "scope": SAMPLE_SCOPE, "document_count": str(count),
                "complete": "true", "format_version": "1"}
        db.executemany("INSERT INTO manifest VALUES (?,?)", rows.items())
        db.commit()
        return count
    finally:
        db.close()


def docs_from_full_index(full_index: Path, doc_ids: list[str]) -> Iterator[dict[str, Any]]:
    db = sqlite3.connect(full_index.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        for doc_id in doc_ids:
            row = db.execute(
                "SELECT doc_id,title,text,metadata FROM docs WHERE doc_id=?", (doc_id,)
            ).fetchone()
            if row:
                yield {"id": row[0], "title": row[1], "text": row[2],
                       "metadata": json.loads(row[3])}
    finally:
        db.close()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()

