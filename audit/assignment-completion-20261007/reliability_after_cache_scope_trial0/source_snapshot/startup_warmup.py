"""Warm real local embeddings/FAISS on one deterministic official corpus document."""
from __future__ import annotations
import hashlib
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any

def warm_engine(engine: Any, corpus: Path) -> dict[str,Any]:
    started=time.perf_counter()
    with closing(sqlite3.connect(corpus.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        row=db.execute('SELECT text FROM docs ORDER BY doc_id LIMIT 1').fetchone()
    if not row or not row[0].strip():raise ValueError('Official corpus warmup input missing')
    text=row[0];loaded=time.perf_counter()
    vector=engine.encoder.encode([text]);encoded=time.perf_counter()
    engine.index.search(vector,1);finished=time.perf_counter()
    return {'completed':True,'selection':'official full docs ORDER BY doc_id LIMIT 1, text only',
        'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'qa_fields_used':[],
        'corpus_read_seconds':loaded-started,'embedding_inference_seconds':encoded-loaded,
        'index_warmup_seconds':finished-encoded,'total_seconds':finished-started,
        'llm_calls':0,'request_budget_created':False}
