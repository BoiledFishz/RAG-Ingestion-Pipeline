"""Repository-level ingestion entry point required by the assignment."""

# ruff: noqa: E402, I001

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rag.ingestion.cli import run


if __name__ == "__main__":
    raise SystemExit(run())
