"""Bounded, traceable answer passages from original TechQA documents."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from rag.techqa.index import tokens

RESOLUTION = re.compile(
    r"(?im)^\s*(?:RESOLVING THE PROBLEM|Problem Solution|ANSWER|LOCAL FIX|"
    r"PROBLEM CONCLUSION|REMEDIATION/FIXES|RESOLUTION)\s*:?\s*\n"
)
BOILERPLATE = re.compile(
    r"(?im)^\s*(?:RELATED INFORMATION|APAR INFORMATION|REFERENCES|"
    r"DISCLAIMER|ACKNOWLEDGEMENTS)\s*\n|\bGET NOTIFIED ABOUT FUTURE SECURITY BULLETINS\b"
)
PRODUCT_VERSIONS = re.compile(r"(?im)^\s*AFFECTED PRODUCTS AND VERSIONS\s*\n")
NEXT_SECTION = re.compile(r"(?m)^\s*[A-Z][A-Z /()_-]{5,}\s*\n")
PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n(?:[ \t]*\n)*")
LIST_ITEM = re.compile(r"(?m)^\s*(?:\d{1,2}[.)]\s+|[-*]\s+\S)")


@dataclass(frozen=True)
class Passage:
    text: str
    relevance: float


def complete_instructions(passage: str, original: str, max_chars: int = 1800) -> str:
    """Keep a list introduction attached to its complete original instruction blocks.

    Ordinary passages retain the 900-character splitter budget. Instruction
    groups may expand to 1800 characters; callers still enforce their serialized
    context budget. An oversized/incomplete group is omitted, never truncated.
    """
    start = original.find(passage)
    if start < 0:
        return ""
    end = start + len(passage)
    tail = PARAGRAPH_BREAK.split(passage)[-1]
    introduction = passage.rstrip(" *").endswith(":")
    if not introduction and not LIST_ITEM.search(tail):
        return passage
    # Recover a step cut by the splitter before considering subsequent steps.
    boundary = PARAGRAPH_BREAK.search(original, end)
    extended_end = boundary.start() if boundary else len(original)
    cursor = boundary.end() if boundary else len(original)
    first_following = introduction
    while cursor < len(original):
        following = PARAGRAPH_BREAK.search(original, cursor)
        block_end = following.start() if following else len(original)
        block = original[cursor:block_end].strip()
        if not block or NEXT_SECTION.match(block + "\n"):
            break
        if not first_following and not LIST_ITEM.match(block):
            break
        extended_end = block_end
        first_following = block.rstrip(" *").endswith(":")
        cursor = following.end() if following else len(original)
    complete = original[start:extended_end].strip()
    if len(complete) > max_chars:
        # Discard preceding explanation if the instruction introduction and
        # complete list can fit together. Never cut off the final list item.
        breaks = list(PARAGRAPH_BREAK.finditer(original, start, end))
        trimmed_start = breaks[-1].end() if breaks else start
        complete = original[trimmed_start:extended_end].strip()
    if len(complete) > max_chars or complete.rstrip(" *").endswith(":"):
        return ""
    return complete


def selection_schema(field: str, identifiers: list[str] | list[int]) -> dict[str, Any]:
    """Encode sufficiency/ID consistency in generation as well as runtime validation."""
    item_type = "integer" if identifiers and isinstance(identifiers[0], int) else "string"
    branches = []
    for sufficient in (True, False):
        branches.append({
            "type": "object", "additionalProperties": False,
            "required": ["sufficient", field],
            "properties": {
                "sufficient": {"type": "boolean", "const": sufficient},
                field: {"type": "array", "items": {"type": item_type, "enum": identifiers},
                        "minItems": 1 if sufficient else 0,
                        "maxItems": 2 if sufficient else 0},
            },
        })
    return {"oneOf": branches}


def answer_passages(
    query: str, text: str, *, limit: int = 4, retrieved_excerpt: str = "",
) -> list[Passage]:
    """Prefer solution sections; never append the rest of a parent as the answer."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    cutoff = BOILERPLATE.search(text)
    usable = text[:cutoff.start()] if cutoff else text
    solutions = list(RESOLUTION.finditer(usable))
    regions = [usable[m.end():solutions[i + 1].start() if i + 1 < len(solutions) else None]
               for i, m in enumerate(solutions)] if solutions else [usable]
    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=80)
    query_words = set(tokens(query))
    ranked = []
    if retrieved_excerpt and retrieved_excerpt in usable:
        start = usable.index(retrieved_excerpt)
        end = start + len(retrieved_excerpt)
        hint_start, hint_end = start, end
        # The legacy index window can start/end mid-word. Expand its edges to
        # paragraph boundaries in the parent before extracting any answer text.
        left = usable.rfind("\n\n", 0, start)
        right = usable.find("\n\n", end)
        start = left + 2 if left >= 0 else 0
        end = right if right >= 0 else len(usable)
        hinted = [usable[start:end]] if not solutions else [
            usable[max(start, match.end()):min(end, (
                solutions[i + 1].start() if i + 1 < len(solutions) else len(usable)
            ))]
            for i, match in enumerate(solutions)
            if match.end() < end and (
                solutions[i + 1].start() if i + 1 < len(solutions) else len(usable)
            ) > start
        ]
        for region in hinted:
            for chunk in splitter.split_text(region):
                overlap = len(query_words & set(tokens(chunk))) / max(len(query_words), 1)
                position = usable.find(chunk, start, end)
                intersection = max(0, min(position + len(chunk), hint_end)
                                   - max(position, hint_start)) if position >= 0 else 0
                ranked.append(Passage(chunk.strip(), 3.0 + overlap
                                      + 0.8 * intersection / max(len(chunk), 1)))
    for region in regions:
        if solutions:
            # Prefer a complete opening answer paragraph over a later keyword-heavy
            # example. A paragraph ending in ':' introduces instructions/table/code
            # and must stay attached to the following content rather than stand alone.
            first = next((p.strip() for p in re.split(r"\n\s*\n", region) if p.strip()), "")
            if (80 <= len(first) <= 900 and not first.rstrip(" *").endswith(":")
                    and not first.casefold().startswith(("see ", "refer to "))):
                overlap = len(query_words & set(tokens(first))) / max(len(query_words), 1)
                ranked.append(Passage(first, 2.0 + overlap))
        for position, chunk in enumerate(splitter.split_text(region)):
            # All chunks remain substrings of the original document, including code/conditions.
            if len(chunk.strip()) < 20 or not any(c.isalpha() for c in chunk):
                continue
            overlap = len(query_words & set(tokens(chunk))) / max(len(query_words), 1)
            score = overlap + (0.35 if solutions else 0) + (
                1.0 if solutions and position == 0 else 0.02 / (position + 1)
            )
            ranked.append(Passage(chunk.strip(), score))
    # A version/exposure question needs the affected versions, not just a fix.
    # Keep this whole section verbatim so compression cannot discard its scope.
    if re.search(r"\b(?:affected|exposed|vulnerable|versions?)\b", query, re.IGNORECASE):
        section = PRODUCT_VERSIONS.search(usable)
        if section:
            following = NEXT_SECTION.search(usable, section.end())
            region = usable[section.start():following.start() if following else None]
            for chunk in splitter.split_text(region):
                overlap = len(query_words & set(tokens(chunk))) / max(len(query_words), 1)
                ranked.append(Passage(chunk.strip(), 4.0 + overlap))
    ranked.sort(key=lambda p: p.relevance, reverse=True)
    selected: list[Passage] = []
    for passage in ranked:
        completed = complete_instructions(passage.text, usable)
        if not completed:
            continue
        passage = Passage(completed, passage.relevance)
        if not any(passage.text in existing.text or existing.text in passage.text
                   for existing in selected):
            selected.append(passage)
        if len(selected) >= limit:
            break
    return selected
