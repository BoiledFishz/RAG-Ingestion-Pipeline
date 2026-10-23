"""Copy the Project 1 MiniLM vectors of a sample's documents into a dense sidecar.

    python -m evaluation.chap12_build_dense --index ../.rag_data/chap12_sample.sqlite
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rag.techqa.data import ROOT

from agents.chap12.dense import build_sidecar


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--semantic", type=Path, default=ROOT / ".rag_data/techqa_semantic")
    args = parser.parse_args()
    destination = args.index.with_suffix(".dense.sqlite")
    print(json.dumps(build_sidecar(args.semantic, args.index, destination), indent=2))


if __name__ == "__main__":
    main()
