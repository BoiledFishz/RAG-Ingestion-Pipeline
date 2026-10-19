"""Cross-encoder reranker for the sample retriever (round 3, 2026-10-18).

The Project 1 reranker scores a weighted sum of a bi-encoder cosine (nomic), term coverage
and a BM25 rank prior. A cross-encoder reads the question and each candidate passage
together and outputs one relevance logit, which is usually better at ordering the top few.

Models are loaded only from local folders written by `.chap12_run/download_ce.py`
(`.rag_data/models/<name>/`, with `ce_manifest.json` recording the Hugging Face repo and the
resolved commit). Nothing is downloaded at runtime. Project 1 code is not modified: this class
has the same `rerank(query, candidates, limit=...)` interface as the other rerankers and is
injected into the existing RetrievalPipeline.
"""

from __future__ import annotations

import asyncio
import json
import math
from dataclasses import replace
from pathlib import Path
from typing import Any

from rag.retrieval.contracts import SearchResult
from rag.techqa.data import ROOT

MODELS = {
    "ce_minilm": "ce_ms_marco_minilm_l6",   # cross-encoder/ms-marco-MiniLM-L-6-v2
    "ce_bge": "ce_bge_reranker_base",       # BAAI/bge-reranker-base
}
MAX_LENGTH = 512
BATCH = 16


def model_dir(choice: str) -> Path:
    return ROOT / ".rag_data/models" / MODELS[choice]


def manifest(choice: str) -> dict[str, Any]:
    path = model_dir(choice) / "ce_manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"{path} missing; run .chap12_run/download_ce.cmd first")
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


class CrossEncoderReranker:
    def __init__(self, choice: str, scorer: Any | None = None) -> None:
        self.choice = choice
        self.identity = manifest(choice) if scorer is None else {"repo": "test"}
        self._scorer = scorer  # injectable for tests: (query, passages) -> list[float]
        self._model: Any = None
        self._tokenizer: Any = None

    def _load(self) -> None:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        path = model_dir(self.choice)
        self._tokenizer = AutoTokenizer.from_pretrained(  # type: ignore[no-untyped-call]
            path, local_files_only=True)
        self._model = AutoModelForSequenceClassification.from_pretrained(
            path, local_files_only=True)
        self._model.eval()

    def score(self, query: str, passages: list[str]) -> list[float]:
        if self._scorer is not None:
            return list(self._scorer(query, passages))
        import torch

        if self._model is None:
            self._load()
        out: list[float] = []
        for start in range(0, len(passages), BATCH):
            batch = passages[start:start + BATCH]
            encoded = self._tokenizer([query] * len(batch), batch, padding=True,
                                      truncation="only_second", max_length=MAX_LENGTH,
                                      return_tensors="pt")
            with torch.no_grad():
                logits = self._model(**encoded).logits
            values = logits[:, 0] if logits.shape[-1] == 1 else logits[:, -1]
            out.extend(1 / (1 + math.exp(-float(v))) for v in values)
        return out

    async def rerank(self, query: str, candidates: list[SearchResult], *,
                     limit: int = 20) -> list[SearchResult]:
        from agents.chap12.budget import charge

        if not candidates or limit <= 0:
            return []
        charge("local")
        passages = [(str(c.metadata.get("context_summary", "")) + " " + c.text).strip()
                    for c in candidates]
        scores = await asyncio.to_thread(self.score, query[:2000], passages)
        ranked = [replace(c, score=s, rerank_score=s, backend=c.backend + f"+{self.choice}")
                  for c, s in zip(candidates, scores, strict=True)]
        ranked.sort(key=lambda r: r.score, reverse=True)
        return [replace(r, rerank_rank=rank) for rank, r in enumerate(ranked[:limit], 1)]
