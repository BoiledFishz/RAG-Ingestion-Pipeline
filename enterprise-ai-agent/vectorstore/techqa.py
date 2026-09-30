"""Official IBM TechQA acquisition, streaming parsing, chunking and indexing."""

from __future__ import annotations

import bz2
import hashlib
import logging
import os
import re
import shutil
import tarfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal

import httpx
import ijson

from models.schemas import Document
from models.settings import PROJECT_ROOT

LOGGER = logging.getLogger(__name__)
TECHQA_URL = (
    "https://huggingface.co/datasets/PrimeQA/TechQA/resolve/main/TechQA.tar.gz?download=true"
)
TECHQA_SHA256 = "6b094ef9a69718f727ce8d7e15c4d961e51032cefaa952e0d6af9d176d7ba118"
ARCHIVE_DEFAULT = PROJECT_ROOT / "data" / "techqa" / "raw" / "TechQA.tar.gz"
EXTRACTED_DEFAULT = PROJECT_ROOT / "data" / "techqa" / "extracted"

CORE_MEMBERS = (
    "TechQA/README.txt",
    "TechQA/CDLA-Permissive-v1.0.pdf",
    "TechQA/training_and_dev/training_Q_A.json",
    "TechQA/training_and_dev/dev_Q_A.json",
    "TechQA/training_and_dev/training_dev_technotes.json",
    "TechQA/validation/validation_questions.json",
    "TechQA/validation/validation_reference.json",
    "TechQA/validation/validation_technotes.json",
)
FULL_MEMBERS = CORE_MEMBERS + (
    "TechQA/technote_corpus/CDLA-Permissive-v1.0.pdf",
    "TechQA/technote_corpus/full_technote_collection.txt.bz2",
)


@dataclass(frozen=True)
class ChunkingConfig:
    size: int = 1200
    overlap: int = 160

    def __post_init__(self) -> None:
        if self.size < 128 or not 0 <= self.overlap < self.size:
            raise ValueError("chunk size must be >=128 and overlap must be smaller than size")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_archive(path: Path, expected: str = TECHQA_SHA256) -> None:
    actual = sha256_file(path)
    if actual.casefold() != expected.casefold():
        raise ValueError(f"TechQA checksum mismatch: expected {expected}, got {actual}")
    LOGGER.info("Verified TechQA archive SHA-256: %s", actual)


def download_archive(destination: Path = ARCHIVE_DEFAULT) -> Path:
    """Resume the official download and verify it before returning."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        verify_archive(destination)
        return destination
    partial = destination.with_suffix(destination.suffix + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    mode = "ab" if offset else "wb"
    with httpx.Client(follow_redirects=True, timeout=None, trust_env=False) as client:
        with client.stream("GET", TECHQA_URL, headers=headers) as response:
            response.raise_for_status()
            if offset and response.status_code != 206:
                LOGGER.warning("Server ignored Range; restarting TechQA download")
                mode = "wb"
            with partial.open(mode) as handle:
                for block in response.iter_bytes(8 * 1024 * 1024):
                    handle.write(block)
    partial.replace(destination)
    verify_archive(destination)
    return destination


def _safe_destination(root: Path, member_name: str) -> Path:
    pure = PurePosixPath(member_name)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"Unsafe archive member: {member_name}")
    destination = (root / Path(*pure.parts)).resolve()
    if root.resolve() not in destination.parents:
        raise ValueError(f"Archive member escapes destination: {member_name}")
    return destination


def extract_archive(
    archive: Path = ARCHIVE_DEFAULT,
    destination: Path = EXTRACTED_DEFAULT,
    *,
    scope: Literal["core", "full"] = "full",
) -> Path:
    """Safely extract only files required for core or complete-corpus operation."""
    verify_archive(archive)
    wanted = set(CORE_MEMBERS if scope == "core" else FULL_MEMBERS)
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as bundle:
        available = {member.name: member for member in bundle.getmembers()}
        missing = wanted - available.keys()
        if missing:
            raise ValueError(f"TechQA archive is missing required members: {sorted(missing)}")
        for name in sorted(wanted):
            member = available[name]
            if not member.isfile() or member.issym() or member.islnk():
                raise ValueError(f"Refusing non-regular archive member: {name}")
            target = _safe_destination(destination, name)
            if target.exists() and target.stat().st_size == member.size:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = bundle.extractfile(member)
            if source is None:
                raise OSError(f"Cannot read archive member: {name}")
            temporary = target.with_suffix(target.suffix + ".part")
            with source, temporary.open("wb") as output:
                shutil.copyfileobj(source, output, length=8 * 1024 * 1024)
            if temporary.stat().st_size != member.size:
                raise OSError(f"Incomplete extraction: {name}")
            temporary.replace(target)
            LOGGER.info("Extracted %s", name)
    return destination / "TechQA"


def _normalize_document(raw: dict[str, Any]) -> dict[str, Any] | None:
    doc_id = str(raw.get("id") or raw.get("_id") or "").strip()
    text = str(raw.get("text") or "").strip()
    if not doc_id or not text:
        return None
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    return {
        "id": doc_id,
        "title": str(raw.get("title") or "").strip(),
        "text": text,
        "metadata": metadata,
    }


def iter_mapping_documents(path: Path) -> Iterator[dict[str, Any]]:
    """Stream documents from the core JSON map without materializing it."""
    with path.open("rb") as handle:
        for key, value in ijson.kvitems(handle, ""):
            if not isinstance(value, dict):
                continue
            value.setdefault("id", key)
            normalized = _normalize_document(value)
            if normalized:
                yield normalized


def iter_full_documents(path: Path) -> Iterator[dict[str, Any]]:
    """Stream every document from IBM's 801,998-document bzip2 corpus.

    The decompressed file contains extremely large top-level JSON arrays. Parsing by line would
    materialize an entire array, so ijson must iterate each array item directly from the bzip2
    stream. ``multiple_values`` also supports archives containing more than one array.
    """

    with bz2.open(path, "rb") as handle:
        for raw in ijson.items(handle, "item", multiple_values=True):
            if isinstance(raw, dict):
                normalized = _normalize_document(raw)
                if normalized:
                    yield normalized


def _split_once(text: str, limit: int) -> tuple[str, int]:
    if len(text) <= limit:
        return text, len(text)
    window = text[:limit]
    best = -1
    for pattern in (r"\n\n+", r"\n", r"(?<=[.!?])\s+", r"\s+"):
        matches = list(re.finditer(pattern, window))
        if matches:
            candidate = matches[-1].start()
            if candidate >= limit // 2:
                best = candidate
                break
    end = best if best > 0 else limit
    return text[:end].strip(), end


def recursive_chunks(text: str, config: ChunkingConfig) -> Iterator[tuple[int, int, str]]:
    """Boundary-aware recursive character chunks with deterministic overlap."""
    cursor = 0
    while cursor < len(text):
        chunk, consumed = _split_once(text[cursor:], config.size)
        if chunk:
            yield cursor, cursor + consumed, chunk
        if cursor + consumed >= len(text):
            break
        cursor += max(1, consumed - config.overlap)


def chunk_technote(raw: dict[str, Any], config: ChunkingConfig) -> Iterator[Document]:
    title, body, doc_id = raw["title"], raw["text"], raw["id"]
    combined = f"{title}\n\n{body}" if title else body
    source = f"techqa://{doc_id}"
    raw_meta = raw.get("metadata", {})
    base: dict[str, str | int | float | bool] = {
        "status": "published",
        "language": "en",
        "document_type": "ibm_technote",
        "dataset": "IBM TechQA",
        "techqa_document_id": doc_id,
        "title": title,
    }
    for key in ("date", "productName", "productId", "canonicalUrl"):
        value = raw_meta.get(key)
        if isinstance(value, (str, int, float, bool)):
            base[key] = value
    for index, (start, end, text) in enumerate(recursive_chunks(combined, config)):
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        yield Document(
            chunk_id=f"techqa:{doc_id}:{index}:{digest[:12]}",
            text=text,
            source_file=source,
            page_number=index + 1,
            metadata={**base, "chunk_index": index, "start_char": start, "end_char": end},
        )


def batched(values: Iterable[Document], size: int) -> Iterator[list[Document]]:
    if size <= 0:
        raise ValueError("batch size must be positive")
    batch: list[Document] = []
    for value in values:
        batch.append(value)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def document_stream(root: Path, scope: Literal["core", "full"]) -> Iterator[dict[str, Any]]:
    if scope == "core":
        yield from iter_mapping_documents(
            root / "training_and_dev" / "training_dev_technotes.json"
        )
        yield from iter_mapping_documents(root / "validation" / "validation_technotes.json")
    else:
        yield from iter_full_documents(
            root / "technote_corpus" / "full_technote_collection.txt.bz2"
        )


def chunks_from_documents(
    documents: Iterable[dict[str, Any]], config: ChunkingConfig
) -> Iterator[Document]:
    for raw in documents:
        yield from chunk_technote(raw, config)


def env_path(name: str, default: Path) -> Path:
    value = Path(os.getenv(name, str(default)))
    return value if value.is_absolute() else PROJECT_ROOT / value
