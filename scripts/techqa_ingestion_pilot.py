"""Separate, resumable 2k-document RCTS/LLM-summary pilot on original TechQA.

Corpus selection hashes document IDs only; questions, answers and labels do not
select documents. This closed pilot cannot establish open full-corpus quality.
It never loads/replaces the complete serving Faiss index.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import heapq
import json
import logging
import sqlite3
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import httpx

from rag.ingestion.chunking import RecursiveChunker
from rag.ingestion.models import ParsedPage
from rag.ingestion.providers import OllamaSummaryProvider
from rag.retrieval.contracts import SearchResult
from rag.techqa.data import ARCHIVE_SHA256, documents
from rag.techqa.retrieval import legacy_chunks

LOGGER = logging.getLogger(__name__)


def prepare(destination: Path, count: int) -> None:
    if not 2000 <= count <= 5000:
        raise ValueError("Use 2000–5000 original documents")
    destination.mkdir(parents=True, exist_ok=False)
    selected: list[tuple[int, str, dict[str, Any]]] = []
    population = 0
    for doc in documents("core"):
        population += 1
        key = int(hashlib.sha256(("techqa-pilot-v1:" + doc["id"]).encode()).hexdigest(), 16)
        item = (-key, doc["id"], doc)
        if len(selected) < count:
            heapq.heappush(selected, item)
        elif item[0] > selected[0][0]:
            heapq.heapreplace(selected, item)
    sample = sorted((item[2] for item in selected), key=lambda d: d["id"])
    raw = "\n".join(json.dumps(doc, ensure_ascii=False, sort_keys=True) for doc in sample) + "\n"
    (destination / "documents.jsonl").write_text(raw, encoding="utf-8")
    chunker = RecursiveChunker(chunk_size=1200, chunk_overlap=160)
    variants = {"legacy_title": [], "rcts_llm": []}
    for doc in sample:
        chunks = legacy_chunks(doc)
        variants["legacy_title"].extend(asdict(c) for c in chunks)
        source = doc["title"] + "\n\n" + doc["text"]
        for chunk in chunker.split_pages([ParsedPage(source, "techqa://" + doc["id"], 1)]):
            key = "techqa-v2:" + doc["id"] + ":" + chunk.chunk_hash
            base = chunks[0]
            meta = {**base.metadata, "chunk_id": key, "chunk_hash": chunk.chunk_hash,
                    "context_summary": "", "schema_version": "pilot-rcts-llm-v2"}
            variants["rcts_llm"].append(asdict(replace(base, text=chunk.text, metadata=meta)))
    for name, chunks in variants.items():
        (destination / f"{name}.jsonl").write_text(
            "\n".join(json.dumps(c, ensure_ascii=False) for c in chunks) + "\n", encoding="utf-8")
    manifest = {"prepared": True, "complete": False, "population": population,
        "documents": len(sample), "source_archive_sha256": ARCHIVE_SHA256,
        "document_sample_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "selection": "smallest SHA256(techqa-pilot-v1:document_id) from unchanged core corpus",
        "scope": "closed source-only sample; not all 801996 docs",
        "chunk_size": 1200, "chunk_overlap": 160,
        "chunks": {name: len(chunks) for name, chunks in variants.items()},
        "summary": "legacy uses official title; RCTS requires actual LLM summary, no fallback",
        "format_limit": "JSON text experiment; not a PDF/OCR parsing test"}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    LOGGER.info("Prepared pilot %s", manifest)


def read_chunks(path: Path) -> list[SearchResult]:
    return [SearchResult(**json.loads(line))
            for line in path.read_text(encoding="utf-8").splitlines()]


def summary_protocol(destination: Path, model: str, digest: str) -> dict[str, Any]:
    return {"script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_sha256": hashlib.sha256(b"".join(p.read_bytes() for p in sorted(
            (Path(__file__).resolve().parents[1] / "src/rag").rglob("*.py")))).hexdigest(),
        "corpus_sha256": hashlib.sha256((destination / "documents.jsonl").read_bytes()).hexdigest(),
        "model": model, "model_digest": digest, "chunk_size": 1200, "overlap": 160}


async def summaries(destination: Path, maximum: int | None) -> bool:
    chunks = read_chunks(destination / "rcts_llm.jsonl")
    model = "llama3.2:3b"
    async with httpx.AsyncClient(timeout=20) as client:
        tags = (await client.get("http://localhost:11434/api/tags")).json()["models"]
    digest = next(t["digest"] for t in tags if t["name"] == model)
    protocol = await asyncio.to_thread(summary_protocol, destination, model, digest)
    protocol_file = destination / "summary_protocol.json"
    if protocol_file.exists() and json.loads(protocol_file.read_text(encoding="utf-8")) != protocol:
        raise ValueError("Pilot code/model/data changed; use a new output, not old summaries")
    if not protocol_file.exists():
        await asyncio.to_thread(protocol_file.write_text, json.dumps(protocol, indent=2),
                                encoding="utf-8")
    provider = OllamaSummaryProvider(model=model, timeout_seconds=120)
    db = sqlite3.connect(destination / "summary-cache.sqlite")
    db.execute("CREATE TABLE IF NOT EXISTS summaries "
               "(hash TEXT, model TEXT, summary TEXT, elapsed_ms REAL, PRIMARY KEY(hash,model))")
    calls, errors, skipped = 0, [], 0
    for chunk in chunks:
        key = str(chunk.metadata["chunk_hash"])
        if db.execute("SELECT 1 FROM summaries WHERE hash=? AND model=?", (key, digest)).fetchone():
            skipped += 1
            continue
        if maximum is not None and calls >= maximum:
            break
        started = time.perf_counter()
        calls += 1
        try:
            summary = await provider.summarize(chunk.text)
            db.execute("INSERT OR IGNORE INTO summaries VALUES (?,?,?,?)",
                       (key, digest, summary, (time.perf_counter()-started)*1000))
            db.commit()
        except (ValueError, RuntimeError, httpx.HTTPError) as exc:
            LOGGER.exception("Pilot summary failed for %s", chunk.chunk_id)
            errors.append({"chunk": chunk.chunk_id, "error": str(exc)})
        if calls % 20 == 0:
            LOGGER.info("Pilot summaries calls=%d failures=%d hash_skips=%d",
                        calls, len(errors), skipped)
    unique = len({str(c.metadata["chunk_hash"]) for c in chunks})
    done = db.execute("SELECT count(*) FROM summaries WHERE model=?", (digest,)).fetchone()[0]
    total_ms = db.execute("SELECT sum(elapsed_ms) FROM summaries WHERE model=?",
                          (digest,)).fetchone()[0]
    db.close()
    state = {"complete": done == unique, "unique_hashes": unique, "completed": done,
             "this_run_calls": calls, "this_run_hash_skips": skipped, "errors": errors,
             "summary_model": model, "model_digest": digest, "cumulative_latency_ms": total_ms}
    await asyncio.to_thread((destination / "summary_progress.json").write_text,
                            json.dumps(state, indent=2), encoding="utf-8")
    return bool(state["complete"])


def encode(destination: Path) -> None:
    import faiss
    import numpy as np

    from rag.techqa.semantic import MiniLMEncoder

    state = json.loads((destination / "summary_progress.json").read_text(encoding="utf-8"))
    if not state["complete"]:
        raise ValueError("LLM summaries are incomplete; do not publish a partial B index")
    db = sqlite3.connect(destination / "summary-cache.sqlite")
    encoder = MiniLMEncoder(device="cpu")
    for variant in ["legacy_title", "rcts_llm"]:
        output = destination / variant
        output.mkdir(exist_ok=False)
        chunks = read_chunks(destination / f"{variant}.jsonl")
        if variant == "rcts_llm":
            chunks = [replace(c, metadata={**c.metadata, "context_summary": db.execute(
                "SELECT summary FROM summaries WHERE hash=? AND model=?",
                (c.metadata["chunk_hash"], state["model_digest"])).fetchone()[0]}) for c in chunks]
        index = faiss.IndexFlatIP(384)
        started = time.perf_counter()
        for offset in range(0, len(chunks), 64):
            vectors = encoder.encode([c.text for c in chunks[offset:offset+64]])
            index.add(np.ascontiguousarray(vectors, dtype="float32"))
        faiss.write_index(index, str(output / "index.faiss"))
        (output / "chunks.json").write_text(json.dumps([asdict(c) for c in chunks],
                                                      ensure_ascii=False), encoding="utf-8")
        (output / "manifest.json").write_text(json.dumps({"complete": True,
            "chunks": len(chunks), "embedding_identity": encoder.identity,
            "embedding_latency_ms": (time.perf_counter()-started)*1000,
            "index_bytes": (output / "index.faiss").stat().st_size,
            "vectors": "original chunk text only; summaries used in bounded reranker"}, indent=2),
            encoding="utf-8")
        del index
    db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=["prepare", "summaries", "encode"], required=True)
    parser.add_argument("--documents", type=int, default=2000)
    parser.add_argument("--max-summaries", type=int)
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare(args.output, args.documents)
    elif args.phase == "summaries":
        LOGGER.info("Pilot summaries complete=%s", asyncio.run(summaries(args.output,
                                                                       args.max_summaries)))
    else:
        encode(args.output)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
