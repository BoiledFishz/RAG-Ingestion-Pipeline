"""Record experimental inputs; reject changed code/config/models on resume."""

from __future__ import annotations

import asyncio
import hashlib
import os
import subprocess
from typing import Any

import httpx

from rag.techqa.data import ARCHIVE_SHA256, ROOT

CONFIG_DEFAULTS = {
    "TECHQA_PROFILE": "full", "TECHQA_DENSE_BACKEND": "semantic",
    "TECHQA_RERANKER": "nomic", "TECHQA_RERANK_WEIGHTS": "0.50,0.30,0.20",
    "TECHQA_GENERATION": "extractive", "MODEL_PROVIDER": "ollama",
    "OLLAMA_MODEL": "qwen2.5:7b", "OLLAMA_NUM_GPU": "auto",
    "TECHQA_FACT_AUDIT": "0", "RETRIEVAL_CANDIDATE_K": "30",
    "RETRIEVAL_RERANK_K": "20", "RRF_RANK_CONSTANT": "60",
    "MAX_CONTEXT_TOKENS": "8000", "MAX_CHUNKS_PER_DOCUMENT": "2",
    "TECHQA_RERANKER_TIMEOUT": "120",
}


def source_protocol() -> dict[str, Any]:
    paths = sorted(path for directory in [ROOT / "src/rag", ROOT / "enterprise-ai-agent",
                                         ROOT / "agentic-rag-homework", ROOT / "scripts"]
                   for path in directory.rglob("*.py") if "__pycache__" not in path.parts)
    code = hashlib.sha256()
    for path in paths:
        code.update(path.relative_to(ROOT).as_posix().encode())
        code.update(path.read_bytes())
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                                cwd=ROOT, capture_output=True, text=True,
                                check=True).stdout.strip())
    return {"git_commit": revision, "tracked_worktree_dirty": dirty,
            "source_sha256": code.hexdigest(), "source_file_count": len(paths),
            "corpus_archive_sha256": ARCHIVE_SHA256,
            "configuration": {key: os.getenv(key, default)
                              for key, default in CONFIG_DEFAULTS.items()},
            "artifact_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                for name in ["config/techqa_thresholds.json",
                             ".rag_data/techqa_semantic/manifest.json"]
                if (ROOT / name).exists()}}


async def runtime_protocol() -> dict[str, Any]:
    result = await asyncio.to_thread(source_protocol)
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get("http://localhost:11434/api/tags")
        response.raise_for_status()
    result["model_digests"] = {model["name"]: model["digest"]
                               for model in response.json()["models"]}
    return result
