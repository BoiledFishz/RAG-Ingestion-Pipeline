"""Recursive, structure-aware chunking with deterministic identity metadata."""

from __future__ import annotations

import hashlib

from rag.ingestion.models import Chunk, ParsedPage


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
                chunks.append(
                    Chunk(
                        text=normalized,
                        metadata={
                            "source_file": page.source_file,
                            "page_number": page.page_number,
                            "chunk_hash": digest,
                            "chunk_ordinal": ordinal,
                            "used_ocr": page.used_ocr,
                        },
                    )
                )
        return chunks
