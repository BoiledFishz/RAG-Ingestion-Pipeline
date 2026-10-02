"""Disk-backed full-corpus BM25 index. Questions/answers never enter the index."""

from __future__ import annotations

import argparse
import json
import logging
import math
import re
import sqlite3
from collections import Counter, OrderedDict
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any

from rag.techqa.data import ARCHIVE_SHA256, INDEX_PATH, documents

LOGGER = logging.getLogger(__name__)
STOP = set(
    "a an and are as at be been but by can could did do does for from had has have how i "
    "if in into is it its may my not of on or our should so that the their them there these "
    "they this to use used using was we were what when where which while why will with "
    "would you your please ibm following problem error question thanks thank help".split()
)


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.casefold()) if len(t) > 1 and t not in STOP]


def build(path: Path = INDEX_PATH, scope: str = "full") -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute("PRAGMA cache_size=-65536")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS docs (
            rowid INTEGER PRIMARY KEY, doc_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL, text TEXT NOT NULL, metadata TEXT NOT NULL);
        CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(
            title, text, content='docs', content_rowid='rowid', tokenize='porter unicode61');
        CREATE TABLE IF NOT EXISTS manifest (key TEXT PRIMARY KEY, value TEXT);
    """)
    manifest = dict(db.execute("SELECT key, value FROM manifest"))
    if manifest.get("complete") == "true":
        if manifest.get("scope") != scope:
            raise ValueError("Scope differs from existing index; choose a separate index path")
        db.close()
        return manifest
    # A failed build resumes document inserts; FTS rebuild runs only after all documents exist.
    count = 0
    batch = []
    try:
        existing = db.execute("SELECT count(*) FROM docs").fetchone()[0]
        complete_documents = scope == "full" and existing == 801996
        for doc in () if complete_documents else documents(scope):
            batch.append((doc["id"], doc["title"], doc["text"], json.dumps(doc["metadata"])))
            count += 1
            if len(batch) == 1000:
                db.executemany(
                    "INSERT OR IGNORE INTO docs(doc_id,title,text,metadata) VALUES (?,?,?,?)", batch
                )
                db.commit()
                batch.clear()
                if count % 50000 == 0:
                    LOGGER.info("TechQA %s: read %d official documents", scope, count)
        db.executemany(
            "INSERT OR IGNORE INTO docs(doc_id,title,text,metadata) VALUES (?,?,?,?)", batch
        )
        db.commit()
        LOGGER.info("Building BM25 postings for %d documents", count)
        db.execute("INSERT INTO search(search) VALUES ('rebuild')")
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS vocabulary USING fts5vocab(search, 'row')")
        actual = db.execute("SELECT count(*) FROM docs").fetchone()[0]
        if scope == "full" and actual != 801996:
            raise ValueError(f"Expected 801996 nonempty full documents, got {actual}")
        manifest = {
            "scope": scope,
            "document_count": str(actual),
            "complete": "true",
            "source_archive_sha256": ARCHIVE_SHA256,
            "format_version": "1",
        }
        db.executemany("INSERT OR REPLACE INTO manifest VALUES (?,?)", manifest.items())
        db.commit()
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return manifest
    finally:
        db.close()


class TechQAIndex:
    def __init__(self, path: Path = INDEX_PATH) -> None:
        self.path = path.resolve()
        self._cache: OrderedDict[tuple[str, int], list[dict[str, Any]]] = OrderedDict()
        self._cache_lock = RLock()
        if not path.is_file():
            raise FileNotFoundError("Run python -m rag.techqa.index --scope full first")
        with self.connect() as db:
            self.manifest = dict(db.execute("SELECT key,value FROM manifest"))
        if self.manifest.get("complete") != "true":
            raise ValueError("TechQA index is incomplete; resume its build")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=30)
        try:
            yield db
        finally:
            db.close()

    def get(self, doc_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT doc_id,title,text,metadata FROM docs WHERE doc_id=?", (doc_id,)
            ).fetchone()
        return self._document(row) if row else None

    @staticmethod
    def _document(row: tuple[Any, ...]) -> dict[str, Any]:
        return {"id": row[0], "title": row[1], "text": row[2], "metadata": json.loads(row[3])}

    def search(self, query: str, limit: int = 30) -> list[dict[str, Any]]:
        """BM25(title weight=3, body=1), over the entire corpus, bounded query vocabulary."""
        key = query, limit
        with self._cache_lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        terms = Counter(tokens(query))
        if not terms or limit <= 0:
            return []
        title_terms = set(tokens(query.splitlines()[0]))
        with self.connect() as db:
            count = int(self.manifest["document_count"])
            weights = {}
            for term in terms:
                row = db.execute("SELECT doc FROM vocabulary WHERE term=?", (term,)).fetchone()
                # Vocabulary stores stems. Unknown inflections retain moderate importance.
                df = row[0] if row else max(10, count // 100)
                weights[term] = math.log1p(count / (df + 1)) * (1.5 if term in title_terms else 1)
            chosen = sorted(terms, key=lambda t: weights[t], reverse=True)[:24]
            expression = " OR ".join('"' + term + '"' for term in chosen)
            rows = db.execute(
                "SELECT d.doc_id,d.title,d.text,d.metadata,ranked.rank "
                "FROM (SELECT rowid,rank FROM search WHERE search MATCH ? "
                "AND rank MATCH 'bm25(3,1)' ORDER BY rank LIMIT ?) ranked "
                "JOIN docs d ON d.rowid=ranked.rowid ORDER BY ranked.rank",
                (expression, limit),
            ).fetchall()
        result = [
            {**self._document(row), "bm25_score": -row[4], "rank": rank}
            for rank, row in enumerate(rows, 1)
        ]
        with self._cache_lock:
            self._cache[key] = result
            if len(self._cache) > 128:
                self._cache.popitem(last=False)
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=["fixture", "core", "full"], default="full")
    parser.add_argument("--path", type=Path, default=INDEX_PATH)
    args = parser.parse_args()
    LOGGER.info("TechQA index manifest: %s", build(args.path.resolve(), args.scope))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
