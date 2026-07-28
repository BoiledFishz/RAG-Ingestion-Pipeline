"""Token-budget-like context assembly with source attribution."""

from __future__ import annotations

from rag.retrieval.contracts import SearchResult


class ContextBuilder:
    def __init__(self, *, max_characters: int = 6_000) -> None:
        if max_characters <= 0:
            raise ValueError("max_characters must be positive")
        self.max_characters = max_characters

    def build(self, results: list[SearchResult]) -> str:
        blocks: list[str] = []
        consumed = 0
        seen: set[str] = set()
        for result in results:
            identity = result.chunk_hash or result.text
            if identity in seen:
                continue
            seen.add(identity)
            source = result.metadata.get("source_file", "unknown")
            page = result.metadata.get("page_number", "?")
            summary = result.metadata.get("context_summary", "")
            prefix = f"[source: {source}, page: {page}]"
            if summary:
                block = f"{prefix}\nContext: {summary}\n{result.text}"
            else:
                block = f"{prefix}\n{result.text}"
            remaining = self.max_characters - consumed
            if remaining <= 0:
                break
            if len(block) > remaining:
                block = block[:remaining].rstrip()
            blocks.append(block)
            consumed += len(block) + 2
        return "\n\n".join(blocks)
