"""Batching must preserve native rankings/content on actual TechQA documents."""

import asyncio
import json
from pathlib import Path

from agents.project2.batched_retrieval import BatchedIndex, BatchedParents
from rag.techqa.index import TechQAIndex
from rag.techqa.retrieval import TechQAParentResolver

ROOT = Path(__file__).resolve().parents[3]


def test_batched_bm25_is_identical_to_native() -> None:
    corpus = ROOT / ".rag_data/techqa_full.sqlite"
    original = TechQAIndex(corpus)
    batched = BatchedIndex(corpus)
    rows = json.loads((ROOT / "specs/project2/v0.2/task_preregistration.json").read_text(encoding="utf-8"))["samples"]
    for sample in rows[-2:]:
        assert batched.search(sample["query"], 30) == original.search(sample["query"], 30)


def test_batched_parent_content_and_order_are_identical() -> None:
    corpus = ROOT / ".rag_data/techqa_full.sqlite"
    index = TechQAIndex(corpus)
    rows = json.loads((ROOT / "specs/project2/v0.2/task_preregistration.json").read_text(encoding="utf-8"))["samples"]
    found = index.search(rows[-1]["query"], 5)
    keys = [f"techqa:{doc['id']}:parent" for doc in found]
    original = asyncio.run(TechQAParentResolver(index).retrieve_by_chunk_ids(keys))
    batched = asyncio.run(BatchedParents(BatchedIndex(corpus)).retrieve_by_chunk_ids(keys))
    assert batched == original
