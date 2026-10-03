"""Read the official archive without inventing documents or question/answer pairs."""

from __future__ import annotations

import bz2
import hashlib
import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import ijson

ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = Path(
    os.getenv("TECHQA_DATA_ROOT", str(ROOT / "enterprise-ai-agent/data/techqa/extracted/TechQA"))
)
FIXTURE_ROOT = ROOT / "data/techqa"
INDEX_PATH = Path(os.getenv("TECHQA_INDEX_PATH", str(ROOT / ".rag_data/techqa_full.sqlite")))
ARCHIVE_SHA256 = "6b094ef9a69718f727ce8d7e15c4d961e51032cefaa952e0d6af9d176d7ba118"


def question_text(row: dict[str, Any]) -> str:
    title = str(row.get("QUESTION_TITLE") or "").strip()
    body = str(row.get("QUESTION_TEXT") or "").strip()
    return title if not body or body == title else f"{title}\n{body}"


def questions(split: str = "dev", root: Path = DATA_ROOT) -> list[dict[str, Any]]:
    names = {
        "train": "training_and_dev/training_Q_A.json",
        "dev": "training_and_dev/dev_Q_A.json",
        "validation": "validation/validation_reference.json",
    }
    if split in {"fixture", "regression"}:
        path = (FIXTURE_ROOT if split == "fixture" else FIXTURE_ROOT / "regression") / (
            "questions.json"
        )
    else:
        path = root / names[split]
    return list(json.loads(path.read_text(encoding="utf-8")))


def normalize(raw: dict[str, Any]) -> dict[str, Any] | None:
    doc_id = str(raw.get("id") or raw.get("_id") or "").strip()
    text = str(raw.get("text") or "").strip()
    if not doc_id or not text:
        return None
    return {
        "id": doc_id,
        "title": str(raw.get("title") or "").strip(),
        "text": text,
        "metadata": raw.get("metadata") or {},
    }


def documents(scope: str = "full", root: Path = DATA_ROOT) -> Iterator[dict[str, Any]]:
    if scope in {"fixture", "regression"}:
        fixture = FIXTURE_ROOT if scope == "fixture" else FIXTURE_ROOT / "regression"
        yield from json.loads((fixture / "documents.json").read_text(encoding="utf-8"))
    elif scope == "full":
        with bz2.open(root / "technote_corpus/full_technote_collection.txt.bz2", "rb") as handle:
            for raw in ijson.items(handle, "item", multiple_values=True):
                doc = normalize(raw)
                if doc:
                    yield doc
    elif scope == "core":
        seen: set[str] = set()
        for name in [
            "training_and_dev/training_dev_technotes.json",
            "validation/validation_technotes.json",
        ]:
            with (root / name).open("rb") as handle:
                for key, raw in ijson.kvitems(handle, ""):
                    raw.setdefault("id", key)
                    doc = normalize(raw)
                    if doc and doc["id"] not in seen:
                        seen.add(doc["id"])
                        yield doc
    else:
        raise ValueError(f"Unknown TechQA scope: {scope}")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
