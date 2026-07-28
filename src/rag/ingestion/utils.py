"""Robust Markdown/PDF parsing and text normalization."""

from __future__ import annotations

import asyncio
import html
import io
import logging
import re
from pathlib import Path

from rag.ingestion.models import ParsedPage

LOGGER = logging.getLogger(__name__)

_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*]\([^)]*\)")
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)]\([^)]*\)")
_MARKDOWN_DECORATION_RE = re.compile(r"(?m)^(?:\s{0,3}#{1,6}\s+|\s*>\s?|\s*[-*_]{3,}\s*$)")
_INLINE_DECORATION_RE = re.compile(r"(?<!\\)(?:\*\*|__|~~|`{1,3})")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(text: str) -> str:
    """Remove HTML/Markdown noise while preserving readable document content."""

    if not text or not text.strip():
        return ""
    value = _SCRIPT_STYLE_RE.sub(" ", text)
    value = _HTML_COMMENT_RE.sub(" ", value)
    value = _MARKDOWN_IMAGE_RE.sub(" ", value)
    value = _MARKDOWN_LINK_RE.sub(r"\1", value)
    value = _HTML_TAG_RE.sub(" ", value)
    value = html.unescape(value)
    value = _MARKDOWN_DECORATION_RE.sub("", value)
    value = _INLINE_DECORATION_RE.sub("", value)
    value = _CONTROL_RE.sub(" ", value)
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


class DocumentParser:
    """Parse supported files without allowing one corrupt document to abort a run."""

    SUPPORTED_SUFFIXES = frozenset({".pdf", ".md", ".markdown"})

    def __init__(
        self,
        *,
        min_native_text_chars: int = 30,
        ocr_languages: str = "eng",
        tesseract_cmd: str | None = None,
        ocr_dpi: int = 300,
    ) -> None:
        self.min_native_text_chars = min_native_text_chars
        self.ocr_languages = ocr_languages
        self.tesseract_cmd = tesseract_cmd
        self.ocr_dpi = ocr_dpi

    async def parse_file(self, path: Path) -> list[ParsedPage]:
        """Return parsed pages, or an empty list for empty, unsupported, or bad files."""

        try:
            if not await asyncio.to_thread(path.is_file):
                LOGGER.warning("Skipping missing or non-file path: %s", path)
                return []
            suffix = path.suffix.lower()
            if suffix not in self.SUPPORTED_SUFFIXES:
                LOGGER.warning("Skipping unsupported file: %s", path)
                return []
            if suffix in {".md", ".markdown"}:
                return await asyncio.to_thread(self._parse_markdown, path)
            return await asyncio.to_thread(self._parse_pdf, path)
        except Exception:
            LOGGER.exception("Parser failed gracefully for %s", path)
            return []

    def _parse_markdown(self, path: Path) -> list[ParsedPage]:
        try:
            raw = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            raw = path.read_text(encoding="latin-1")
            LOGGER.warning("Decoded %s with latin-1 fallback", path)
        text = clean_text(raw)
        if not text:
            LOGGER.warning("No usable text found in Markdown file %s", path)
            return []
        return [ParsedPage(text=text, source_file=path.name, page_number=1)]

    def _parse_pdf(self, path: Path) -> list[ParsedPage]:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path), strict=False)
        except Exception:
            LOGGER.exception("Unable to open PDF %s", path)
            return []

        pages: list[ParsedPage] = []
        for index, page in enumerate(reader.pages):
            page_number = index + 1
            used_ocr = False
            try:
                native_text = clean_text(page.extract_text() or "")
            except Exception:
                LOGGER.warning("Native extraction failed for %s page %d", path, page_number)
                native_text = ""

            text = native_text
            if len(native_text) < self.min_native_text_chars:
                LOGGER.info("Using OCR fallback for %s page %d", path.name, page_number)
                text = clean_text(self._ocr_pdf_page(path, index))
                used_ocr = bool(text)
            if not text:
                LOGGER.warning("No text extracted from %s page %d", path, page_number)
                continue
            pages.append(
                ParsedPage(
                    text=text,
                    source_file=path.name,
                    page_number=page_number,
                    used_ocr=used_ocr,
                )
            )
        return pages

    def _ocr_pdf_page(self, path: Path, page_index: int) -> str:
        """Render one PDF page and run OCR; missing native tools degrade to empty text."""

        try:
            import fitz
            import pytesseract
            from PIL import Image

            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            with fitz.open(path) as document:
                page = document.load_page(page_index)
                scale = self.ocr_dpi / 72
                pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                image = Image.open(io.BytesIO(pixmap.tobytes("png")))
                return str(pytesseract.image_to_string(image, lang=self.ocr_languages))
        except Exception:
            LOGGER.exception("OCR fallback failed for %s page %d", path, page_index + 1)
            return ""
