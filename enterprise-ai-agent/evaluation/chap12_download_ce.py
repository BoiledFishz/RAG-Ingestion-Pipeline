"""Download the two cross-encoder rerankers into .rag_data/models (round 3).

    python -m evaluation.chap12_download_ce

Skips a model whose folder already has ce_manifest.json. Records the Hugging Face repo and the
resolved commit SHA so later runs are tied to exact weights. Only weights, config and
tokenizer files are fetched (safetensors preferred).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from agents.chap12.cross_encoder import MODELS, model_dir

REPOS = {"ce_minilm": "cross-encoder/ms-marco-MiniLM-L-6-v2",
         "ce_bge": "BAAI/bge-reranker-base"}
PATTERNS = ["*.json", "*.txt", "*.model", "model.safetensors"]


def main() -> None:
    from huggingface_hub import HfApi, snapshot_download

    for choice in MODELS:
        target = model_dir(choice)
        manifest = target / "ce_manifest.json"
        if manifest.is_file():
            print(choice, "present", json.loads(manifest.read_text("utf-8"))["revision"])
            continue
        repo = REPOS[choice]
        revision = HfApi().model_info(repo).sha
        snapshot_download(repo, revision=revision, local_dir=target, allow_patterns=PATTERNS)
        if not (target / "model.safetensors").is_file():
            snapshot_download(repo, revision=revision, local_dir=target,
                              allow_patterns=["pytorch_model.bin"])
        size = sum(p.stat().st_size for p in target.rglob("*") if p.is_file())
        manifest.write_text(json.dumps({
            "choice": choice, "repo": repo, "revision": revision, "bytes": size,
            "downloaded_utc": datetime.now(UTC).isoformat()}, indent=1) + "\n",
            encoding="utf-8")
        print(choice, repo, revision, size)


if __name__ == "__main__":
    main()
