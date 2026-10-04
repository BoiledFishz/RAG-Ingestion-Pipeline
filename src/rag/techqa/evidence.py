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
    start_char: int = -1
    end_char: int = -1
    section: str = ""
    covers: tuple[str, ...] = ()
    instruction_group: bool = False


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


def aspect_passages(
    query: str, text: str, *, limit: int = 2, retrieved_excerpt: str = "",
    max_chars: int = 3600,
) -> list[Passage]:
    """Select complementary original spans across ALL relevant parent sections.

    Coverage is a query-derived ranking hint, not a sufficiency verdict. At most
    two spans from one document are selected; every span has exact original offsets.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    from rag.techqa.facts import potential_coverage, required_facts

    if limit <= 0:
        return []
    limit = min(2, limit)
    cutoff = BOILERPLATE.search(text)
    usable = text[:cutoff.start()] if cutoff else text
    if len(required_facts(query)) == 1:
        # Preserve the established direct-answer ordering for ordinary questions.
        return [Passage(p.text, p.relevance, text.find(p.text),
                        text.find(p.text) + len(p.text), "", potential_coverage(query, p.text),
                        bool(LIST_ITEM.search(p.text)))
                for p in answer_passages(query, text, limit=limit,
                                         retrieved_excerpt=retrieved_excerpt)]
    facts = {f.key for f in required_facts(query)}

    def unit(start: int, end: int, section: str) -> Passage | None:
        value = usable[start:end].strip()
        note = re.search(r"\bNote:\s", value)
        if note:
            value = value[:note.start()].rstrip()
        if not value or len(value) > max_chars:
            return None
        offset = usable.find(value, start, end)
        return Passage(value, len(potential_coverage(query, value)), offset,
                       offset + len(value), section, potential_coverage(query, value),
                       bool(LIST_ITEM.search(value)))

    # These are document structures, not named-product or dataset-ID rules.
    # A bulletin's details, exposure table and fixes are one bounded contiguous span.
    if "vulnerability" in facts:
        details = re.search(r"(?im)^\s*VULNERABILITY DETAILS\s*\n", usable)
        if details:
            whole = unit(details.start(), len(usable), "vulnerability/exposure/remediation")
            if whole:
                return [whole]
    # Each explicit product-version selection section has different fact values,
    # even though they share the same selection_rule slot.
    if "selection_rule" in facts:
        versions = list(re.finditer(r"(?m)^[^\n]{0,65}\sV\d+(?:\.\d+)+\s*\n", usable))
        choices = [unit(h.start(), versions[i + 1].start() if i + 1 < len(versions)
                        else len(usable), h[0].strip()) for i, h in enumerate(versions)]
        complete = [p for p in choices if p and "selection_rule" in p.covers]
        if complete:
            return complete[:limit]
    # Shared setup steps + the query's version branch form one complete procedure.
    releases = list(re.finditer(r"(?m)^[^\n]{0,65}\bRelease\s+(\d+)\b", usable))
    wanted = set(re.findall(r"\b[A-Za-z]+\s+(\d{2})(?![\d.])", query))
    if releases and wanted:
        match = next(((i, h) for i, h in enumerate(releases) if h[1] in wanted), None)
        resolution = RESOLUTION.search(usable)
        if match and resolution:
            i, heading = match
            end = releases[i + 1].start() if i + 1 < len(releases) else len(usable)
            validation = re.search(r"(?im)^To confirm\b", usable[heading.start():end])
            if validation:
                end = heading.start() + validation.start()
            setup = unit(resolution.end(), releases[0].start(), "shared procedure setup")
            branch = unit(heading.start(), end, heading[0].strip())
            if setup and branch and limit >= 2:
                return [setup, branch]
    if "configured_identity" in facts:
        alias = re.search(r"(?im)^Default component.managed authentication alias[^\n]*", usable)
        if alias:
            following = re.search(r"(?im)^Authentication alias for inbound\b", usable[alias.end():])
            end = alias.end() + following.start() if following else len(usable)
            procedure = unit(alias.start(), end, "outbound identity configuration")
            default = re.search(r"(?im)^Default behavio\w* when no credentials[^\n]*", usable)
            cause = None
            if default:
                following = re.search(r"(?im)^Container.managed security[^\n]*",
                                      usable[default.end():])
                if following:
                    cause = unit(default.start(), default.end() + following.start(),
                                 "default outbound identity condition")
            if procedure:
                return ([cause, procedure] if cause and limit >= 2 else [procedure])
    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=80)
    words = set(tokens(query))
    requested_releases = set(re.findall(
        r"(?:release|version|\b[A-Z][A-Za-z]+)\s+(\d{2})(?![\d.])", query,
        re.IGNORECASE))
    headings = list(re.finditer(
        r"(?m)^\s*(?:[A-Z][A-Z /()_-]{5,}|[^\n]{0,65}\b(?:Release|V)\s*"
        r"\d+(?:\.\d+)*[^\n]{0,8})\s*(?=\n)", usable))
    candidates: dict[str, Passage] = {}

    def add(value: str, bonus: float = 0) -> None:
        value = value.strip()
        start = usable.find(value)
        if start < 0 or len(value) < 20 or len(value) > max_chars:
            return
        release = re.match(r".*\bRelease\s+(\d+)\b", value.splitlines()[0], re.IGNORECASE)
        if release and requested_releases and release[1] not in requested_releases:
            return
        # A note after a flattened part-number table is a new paragraph, not a step.
        note = re.search(r"\bNote:\s", value)
        if note:
            value = value[:note.start()].rstrip()
        complete = complete_instructions(value, usable, max_chars=max_chars)
        if not complete:
            # A shared preamble can end at a version branch. It is a dependency
            # of the matching version procedure, not a standalone complete answer.
            if not (LIST_ITEM.search(value) and value.rstrip().endswith(":")
                    and requested_releases):
                return
            complete = value
        value = complete
        releases = set(re.findall(r"\bRelease\s+(\d+)\b", value, re.IGNORECASE))
        if requested_releases and releases and not releases <= requested_releases:
            return
        start = usable.find(value)
        covers = potential_coverage(query, value)
        overlap = len(words & set(tokens(value))) / max(len(words), 1)
        noise = len(re.findall(r"https?://|\[/support/", value)) * 0.5
        heading = next((h[0].strip() for h in reversed(headings) if h.start() <= start), "")
        score = len(covers) * 2.0 + overlap - noise + bonus
        if requested_releases and releases == requested_releases:
            score += 2.0
        if RESOLUTION.search(heading + "\n"):
            score += 0.35
        if retrieved_excerpt and value in retrieved_excerpt:
            score += 0.15  # A positional hint cannot outweigh a missing required aspect.
        candidates[value] = Passage(value, score, start, start + len(value), heading,
                                    covers, bool(LIST_ITEM.search(value)))

    for value in splitter.split_text(usable):
        add(value)
    for passage in answer_passages(query, text, limit=12, retrieved_excerpt=retrieved_excerpt):
        add(passage.text, min(2, passage.relevance))
    # Whole bounded sections retain version tables and named procedure alternatives.
    for i, heading in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(usable)
        add(usable[heading.start():end])
    # Merge nearby complementary spans, retaining intervening conditions verbatim.
    initial = sorted(candidates.values(), key=lambda p: -p.relevance)[:24]
    for left in initial:
        for right in initial:
            if (left.start_char < right.start_char and right.end_char - left.start_char <= max_chars
                    and set(right.covers) - set(left.covers)):
                add(usable[left.start_char:right.end_char])
    selected: list[Passage] = []
    covered: set[str] = set()
    while candidates and len(selected) < limit:
        ranked = sorted(candidates.values(), key=lambda p: (
            -(len(set(p.covers) - covered) * 3 + p.relevance), len(p.text), p.start_char))
        chosen = ranked[0]
        if selected and not set(chosen.covers) - covered:
            # Different halves of a versioned procedure cover the same fact slot
            # but contain complementary command steps. Keep the original preamble.
            continuations = [p for p in ranked if p.instruction_group
                             and requested_releases and not re.search(
                                 r"\bRelease\s+\d+\b", p.text, re.IGNORECASE)]
            if not continuations:
                break
            chosen = continuations[0]
        selected.append(chosen)
        covered.update(chosen.covers)
        candidates = {k: p for k, p in candidates.items()
                      if not (p.text in chosen.text or chosen.text in p.text)
                      and len(set(tokens(p.text)) & set(tokens(chosen.text)))
                      / max(len(set(tokens(p.text)) | set(tokens(chosen.text))), 1) < 0.82}
    return sorted(selected, key=lambda p: p.start_char)
