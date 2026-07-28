"""Budgeted context assembly, parent expansion, and citation validation."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from rag.retrieval.contracts import ParentResolver, SearchResult

_TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]+|[\u4e00-\u9fff]|[^\s]")
_CITATION_RE = re.compile(r"\[(S\d+)]")


def count_tokens(text: str) -> int:
    """Return a deterministic tokenizer-independent budget estimate."""

    return len(_TOKEN_RE.findall(text))


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    if max_tokens <= 0:
        return ""
    matches = list(_TOKEN_RE.finditer(text))
    if len(matches) <= max_tokens:
        return text
    return text[: matches[max_tokens - 1].end()].rstrip()


@dataclass(frozen=True, slots=True)
class Citation:
    source_id: str
    chunk_id: str
    source_file: str
    page_number: int | str


@dataclass(frozen=True, slots=True)
class ContextBuildResult:
    context: str
    source_map: dict[str, Citation]
    selected_results: list[SearchResult]
    token_count: int


@dataclass(frozen=True, slots=True)
class CitationValidation:
    valid: bool
    referenced_source_ids: tuple[str, ...]
    invalid_source_ids: tuple[str, ...]


class CitationValidator:
    def validate(
        self,
        answer: str,
        source_map: dict[str, Citation],
        *,
        require_citation: bool = True,
    ) -> CitationValidation:
        referenced = tuple(dict.fromkeys(_CITATION_RE.findall(answer)))
        invalid = tuple(source_id for source_id in referenced if source_id not in source_map)
        valid = not invalid and (bool(referenced) or not require_citation)
        return CitationValidation(
            valid=valid,
            referenced_source_ids=referenced,
            invalid_source_ids=invalid,
        )


class ContextBuilder:
    def __init__(
        self,
        *,
        max_context_tokens: int = 8_000,
        max_chunks_per_document: int = 2,
        max_characters: int | None = None,
    ) -> None:
        if max_characters is not None:
            if max_characters <= 0:
                raise ValueError("max_characters must be positive")
            max_context_tokens = max(1, max_characters // 4)
        if max_context_tokens <= 0:
            raise ValueError("max_context_tokens must be positive")
        if max_chunks_per_document <= 0:
            raise ValueError("max_chunks_per_document must be positive")
        self.max_context_tokens = max_context_tokens
        self.max_chunks_per_document = max_chunks_per_document

    def build(self, results: list[SearchResult]) -> str:
        """Compatibility helper returning only the serialized context."""

        return self.build_context(results).context

    async def build_with_parents(
        self,
        results: list[SearchResult],
        *,
        parent_resolver: ParentResolver | None = None,
    ) -> ContextBuildResult:
        expanded = results
        if parent_resolver is not None:
            parent_ids = list(
                dict.fromkeys(
                    str(result.metadata["parent_id"])
                    for result in results
                    if result.metadata.get("parent_id")
                )
            )
            if parent_ids:
                parents = await parent_resolver.retrieve_by_chunk_ids(parent_ids)
                by_id = {parent.chunk_id: parent for parent in parents}
                expanded = [
                    self._replace_with_parent(result, by_id) for result in results
                ]
        return self.build_context(expanded)

    @staticmethod
    def _replace_with_parent(
        child: SearchResult, parents: dict[str, SearchResult]
    ) -> SearchResult:
        parent_id = str(child.metadata.get("parent_id", ""))
        parent = parents.get(parent_id)
        if parent is None:
            return child
        metadata = {**parent.metadata, "child_chunk_id": child.chunk_id}
        return replace(parent, metadata=metadata, retrieval_rank=child.retrieval_rank)

    def build_context(self, results: list[SearchResult]) -> ContextBuildResult:
        opening = "<retrieved_context>\n"
        closing = "\n</retrieved_context>"
        fixed_tokens = count_tokens(opening + closing)
        if not results or fixed_tokens >= self.max_context_tokens:
            return ContextBuildResult("", {}, [], 0)

        blocks: list[str] = []
        source_map: dict[str, Citation] = {}
        selected: list[SearchResult] = []
        seen_chunks: set[str] = set()
        per_document: dict[str, int] = {}

        for result in results:
            chunk_id = result.chunk_id or result.text
            if chunk_id in seen_chunks:
                continue
            source_file = str(result.metadata.get("source_file", "unknown"))
            if per_document.get(source_file, 0) >= self.max_chunks_per_document:
                continue

            source_id = f"S{len(blocks) + 1}"
            page_number = result.metadata.get("page_number", "?")
            summary = str(result.metadata.get("context_summary", "")).strip()
            header = f"[{source_id}] [source: {source_file}, page: {page_number}]"
            payload = f"Context summary: {summary}\n{result.text}" if summary else result.text

            current = opening + "\n\n".join(blocks) + closing
            separator_tokens = count_tokens("\n\n") if blocks else 0
            remaining = (
                self.max_context_tokens
                - count_tokens(current)
                - separator_tokens
                - count_tokens(header + "\n")
            )
            payload = truncate_to_tokens(payload, remaining)
            if not payload:
                break

            block = f"{header}\n{payload}"
            proposed = opening + "\n\n".join([*blocks, block]) + closing
            if count_tokens(proposed) > self.max_context_tokens:
                break

            blocks.append(block)
            seen_chunks.add(chunk_id)
            per_document[source_file] = per_document.get(source_file, 0) + 1
            selected.append(result)
            source_map[source_id] = Citation(
                source_id=source_id,
                chunk_id=result.chunk_id,
                source_file=source_file,
                page_number=page_number if isinstance(page_number, (int, str)) else "?",
            )

        if not blocks:
            return ContextBuildResult("", {}, [], 0)
        context = opening + "\n\n".join(blocks) + closing
        return ContextBuildResult(
            context=context,
            source_map=source_map,
            selected_results=selected,
            token_count=count_tokens(context),
        )
