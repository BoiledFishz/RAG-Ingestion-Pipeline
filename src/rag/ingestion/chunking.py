"""Recursive, structure-aware chunking with deterministic identity metadata."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from rag.ingestion.models import Chunk, ParsedPage

_CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")


class RecursiveChunker:
    """Wrap LangChain's recursive splitter and enforce required metadata."""

    def __init__(self, *, chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be >= 0 and smaller than chunk_size")
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
            separators=["\n\n", "\n", ". ", "。", "; ", "；", ", ", "，", " ", ""],
        )

    def split_pages(self, pages: list[ParsedPage]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for page in pages:
            for ordinal, text in enumerate(self._splitter.split_text(page.text)):
                normalized = text.strip()
                if not normalized:
                    continue
                digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
                suffix = Path(page.source_file).suffix.lower()
                document_type = "pdf" if suffix == ".pdf" else "markdown"
                language = "zh-CN" if _CHINESE_RE.search(normalized) else "en"
                chunks.append(
                    Chunk(
                        text=normalized,
                        metadata={
                            "source_file": page.source_file,
                            "page_number": page.page_number,
                            "chunk_hash": digest,
                            "chunk_id": digest,
                            "chunk_ordinal": ordinal,
                            "used_ocr": page.used_ocr,
                            "document_type": document_type,
                            "language": language,
                            "status": "published",
                        },
                    )
                )
        return chunks
