"""Assignment-required smoke tests for cleaning and graceful parser failure."""

from __future__ import annotations

import asyncio
from pathlib import Path

from utils import DocumentParser, clean_text


def test_clean_text_removes_html_and_markdown_noise() -> None:
    dirty = """# Heading
<script>danger()</script><b>AWS</b> **support** [guide](https://example.invalid)
![tracking pixel](pixel.png) <!-- hidden -->
"""
    cleaned = clean_text(dirty)
    assert cleaned == "Heading\nAWS support guide"
    assert "danger" not in cleaned
    assert "http" not in cleaned


def test_parser_returns_empty_for_empty_and_bad_files(tmp_path: Path) -> None:
    empty = tmp_path / "empty.md"
    empty.write_text("   \n<!-- only a comment -->", encoding="utf-8")
    bad_pdf = tmp_path / "broken.pdf"
    bad_pdf.write_bytes(b"this is not a PDF")
    parser = DocumentParser()

    assert asyncio.run(parser.parse_file(empty)) == []
    assert asyncio.run(parser.parse_file(bad_pdf)) == []
