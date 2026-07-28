"""Compatibility exports for the assignment's requested top-level utils.py."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rag.ingestion.models import ParsedPage  # noqa: E402
from rag.ingestion.utils import DocumentParser, clean_text  # noqa: E402

__all__ = ["DocumentParser", "ParsedPage", "clean_text"]
