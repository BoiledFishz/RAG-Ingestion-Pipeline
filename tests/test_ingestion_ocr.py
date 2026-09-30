from __future__ import annotations

import asyncio
from pathlib import Path

import fitz
from pytest import MonkeyPatch

from rag.ingestion.utils import DocumentParser


def test_image_only_pdf_uses_ocr_fallback(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    path = tmp_path / "scan.pdf"
    document = fitz.open()
    document.new_page()
    document.save(path)
    document.close()

    calls: list[tuple[Path, int]] = []
    parser = DocumentParser(min_native_text_chars=30)

    def fake_ocr(source: Path, page_index: int) -> str:
        calls.append((source, page_index))
        return "Recovered text from an image-only support document."

    monkeypatch.setattr(parser, "_ocr_pdf_page", fake_ocr)
    pages = asyncio.run(parser.parse_file(path))

    assert calls == [(path, 0)]
    assert len(pages) == 1
    assert pages[0].used_ocr is True
    assert pages[0].text.startswith("Recovered text")
