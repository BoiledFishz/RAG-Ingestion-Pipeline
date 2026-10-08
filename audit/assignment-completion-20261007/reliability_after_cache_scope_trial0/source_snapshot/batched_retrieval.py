"""Project 2-only SQL batching, preserving native scoring and source identity.

The old defaults are unchanged. These are adapters of existing indices and
reranking, not a new corpus, a new retriever algorithm or a result cache.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import sqlite3
from collections import Counter
from contextlib import closing
from dataclasses import replace
from typing import Any

from agents.project2.cache_identity import current_identity, embedding_key

from rag.retrieval.filters import FilterPolicy
from rag.techqa.embedding_server import SemanticSearch
from rag.techqa.index import TechQAIndex, tokens
from rag.techqa.retrieval import TechQAParentResolver, TechQAReranker, legacy_chunks


class BatchedIndex(TechQAIndex):
    def search(self, query: str, limit: int = 30) -> list[dict[str, Any]]:
        identity = current_identity()
        key = json.dumps([identity, query]), limit
        with self._cache_lock:
            if identity is not None and key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        terms = Counter(tokens(query))
        if not terms or limit <= 0:
            return []
        title_terms = set(tokens(query.splitlines()[0]))
        with self.connect() as db:
            marks = ",".join("?" for _ in terms)
            frequencies = dict(db.execute(f"SELECT term,doc FROM vocabulary WHERE term IN ({marks})", tuple(terms)))
            total = int(self.manifest["document_count"])
            weights = {term: math.log1p(total/(frequencies.get(term, max(10, total//100))+1)) * (1.5 if term in title_terms else 1) for term in terms}
            chosen = sorted(terms, key=lambda term: weights[term], reverse=True)[:24]
            expression = " OR ".join('"'+term+'"' for term in chosen)
            rows = db.execute("SELECT d.doc_id,d.title,d.text,d.metadata,ranked.rank FROM (SELECT rowid,rank FROM search WHERE search MATCH ? AND rank MATCH 'bm25(3,1)' ORDER BY rank LIMIT ?) ranked JOIN docs d ON d.rowid=ranked.rowid ORDER BY ranked.rank", (expression, limit)).fetchall()
        result = [{**self._document(row), "bm25_score": -row[4], "rank": rank} for rank, row in enumerate(rows, 1)]
        if identity is None:
            return result
        with self._cache_lock:
            self._cache[key] = result
            if len(self._cache) > 128:
                self._cache.popitem(last=False)
        return result

    def get_many(self, ids: list[str]) -> dict[str, dict[str, Any]]:
        if not ids:
            return {}
        if len(ids) > 100:
            raise ValueError("Only bounded retrieved parent candidates allowed")
        marks = ",".join("?" for _ in ids)
        with self.connect() as db:
            rows = db.execute(f"SELECT doc_id,title,text,metadata FROM docs WHERE doc_id IN ({marks})", tuple(ids)).fetchall()
        return {row[0]: self._document(row) for row in rows}


class BatchedParents(TechQAParentResolver):
    async def retrieve_by_chunk_ids(self, chunk_ids: list[str]) -> Any:
        keys = [key for key in dict.fromkeys(chunk_ids) if re.fullmatch(r"techqa:[^:]+:parent", key)]
        documents = await asyncio.to_thread(self.index.get_many, [key.split(":")[1] for key in keys])
        results = []
        for key in keys:
            doc = documents.get(key.split(":")[1])
            if doc:
                base = legacy_chunks(doc)[0]
                text = doc["title"]+"\n\n"+doc["text"]
                metadata = {**base.metadata, "chunk_id": key, "page_number": 1, "chunk_hash": hashlib.sha256(text.encode()).hexdigest()}
                metadata.pop("parent_id", None)
                results.append(replace(base, text=text, metadata=metadata))
        return results


class BatchedSemanticSearch(SemanticSearch):
    def search(self, request: Any) -> Any:
        import faiss

        from rag.techqa.embedding_server import metadata_connection

        filters = FilterPolicy().apply(request.filters)
        if filters.get("source_file") is not None:
            return super().search(request)
        if any(filters.get(key, value) != value for key, value in {"status": "published", "language": "en", "document_type": "ibm_technote"}.items()):
            return []
        faiss.omp_set_num_threads(4)
        vector = self.encoder.encode([request.query])
        scores, identifiers = self.index.search(vector, request.limit)
        valid = [int(identifier)+1 for identifier in identifiers[0] if identifier >= 0]
        if not valid:
            return []
        marks = ",".join("?" for _ in valid)
        with closing(metadata_connection(self.path)) as db:
            rows = {row[0]: row[1:] for row in db.execute(f"SELECT rowid,text,metadata FROM chunks WHERE rowid IN ({marks})", tuple(valid))}
        result = []
        for score, identifier in zip(scores[0], identifiers[0], strict=True):
            if identifier < 0:
                continue
            row = rows.get(int(identifier)+1)
            if row is None:
                raise ValueError("Missing metadata for semantic result")
            result.append({"text": row[0], "metadata": json.loads(row[1]), "score": float(score)})
        return result


class BatchedReranker(TechQAReranker):
    async def embeddings(self, texts: list[str]) -> list[list[float]]:
        identity = current_identity()
        if identity is None:
            return await self.embedder.embed_documents(texts)
        data_version, scope = identity
        keys = [embedding_key(self.embedder.model, text, data_version, scope) for text in texts]
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.cache)) as db:
            # Inherits the actual existing cache, not a new result cache.
            db.execute("CREATE TABLE IF NOT EXISTS embeddings (key TEXT PRIMARY KEY, vector TEXT)")
            marks = ",".join("?" for _ in keys)
            found = {key: json.loads(vector) for key, vector in db.execute(f"SELECT key,vector FROM embeddings WHERE key IN ({marks})", tuple(keys))}
        missing = list(dict.fromkeys(key for key in keys if key not in found))
        if missing:
            vectors = await self.embedder.embed_documents([texts[keys.index(key)] for key in missing])
            found.update(zip(missing, vectors, strict=True))
            with closing(sqlite3.connect(self.cache)) as db:
                marks = ",".join("(?,?)" for _ in missing)
                values = tuple(value for key in missing for value in (key, json.dumps(found[key])))
                db.execute(f"INSERT OR IGNORE INTO embeddings VALUES {marks}", values)
                db.commit()
        return [found[key] for key in keys]
