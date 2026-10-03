"""Query-aware sentence extraction, with provenance and a serialized-context budget."""

from __future__ import annotations

import re

from agents.rag_agent.text import serialize_evidence, terms, token_count
from models.schemas import CompressionResult, Document, Evidence

INSTRUCTION_PATTERN = re.compile(
    r"ignore (?:all |previous |prior )?instructions|system prompt|reveal.*secret|忽略.*指令",
    re.IGNORECASE,
)


class ContextCompressor:
    def __init__(
        self,
        max_tokens: int = 900,
        max_sources: int = 4,
        min_relevance: float = 0.20,
        model_selects_evidence: bool = False,
    ) -> None:
        if max_tokens <= 0 or not 1 <= max_sources <= 8 or not 0 <= min_relevance <= 1:
            raise ValueError("invalid compression settings")
        self.max_tokens, self.max_sources = max_tokens, max_sources
        self.min_relevance = min_relevance
        self.model_selects_evidence = model_selects_evidence

    def compress(self, query: str, candidates: list[Document]) -> CompressionResult:
        if any(d.metadata.get("_full_parent") for d in candidates):
            from rag.techqa.settings import evidence_candidate_threshold, relevance_threshold

            candidates = [
                d
                for d in candidates
                if d.score >= (
                    min(evidence_candidate_threshold(), float(
                        d.metadata.get("_acceptance_threshold", relevance_threshold())))
                    if self.model_selects_evidence else
                    float(d.metadata.get("_acceptance_threshold", relevance_threshold()))
                )
            ]
            from rag.techqa.evidence import answer_passages

            resolved: list[Evidence] = []
            seen_passages: set[str] = set()
            for document in candidates:
                for passage in answer_passages(
                    query, document.text, limit=1,
                    retrieved_excerpt=str(document.metadata.get("_retrieved_excerpt", "")),
                ):
                    if passage.text in seen_passages:
                        continue
                    evidence = Evidence(
                        source_id=f"S{len(resolved) + 1}",
                        chunk_id=document.chunk_id,
                        source_file=document.source_file,
                        page_number=document.page_number,
                        excerpt=passage.text,
                        title=str(document.metadata.get("title", "")),
                        applicability=document.text[:500],
                        relevance=min(1, max(0, document.score)),
                        tokens=token_count(passage.text),
                    )
                    if token_count(serialize_evidence([*resolved, evidence])) > self.max_tokens:
                        continue
                    resolved.append(evidence)
                    seen_passages.add(passage.text)
                if len(resolved) >= self.max_sources:
                    break
            return CompressionResult(
                evidence=resolved,
                original_tokens=sum(token_count(d.text) for d in candidates),
                context_tokens=token_count(serialize_evidence(resolved)) if resolved else 0,
            )
        original_tokens = sum(token_count(d.text) for d in candidates)
        query_terms = terms(query)
        anchors = {
            value.casefold()
            for value in re.findall(
                r"\b[A-Za-z0-9_.-]+:[A-Za-z0-9_*.-]+\b|"
                r"\b[A-Za-z][a-z]+(?:[A-Z][A-Za-z0-9]+)+\b",
                query,
            )
        }
        topical = candidates
        versions = re.findall(r"\b\d+(?:\.\d+){1,4}\b", query)
        if versions:
            topical = [
                d
                for d in candidates
                if all(
                    re.search(r"(?<![\d.])" + re.escape(version) + r"(?![\d.])", d.text)
                    for version in versions
                )
            ]
        vocabulary = set().union(*(terms(d.text) for d in topical)) if topical else set()
        # Reject questions whose main vocabulary is absent, not merely a matching service name.
        # This conservative lexical coverage gate is explicit and evaluated, not a truth model.
        if len(query_terms & vocabulary) / max(len(query_terms), 1) < 0.5:
            return CompressionResult(original_tokens=original_tokens)
        ranked: list[tuple[float, int, Document, str]] = []
        for rank, document in enumerate(topical):
            for sentence in re.split(r"(?<=[.!?。！？])\s+|\n+", document.text):
                excerpt = sentence.strip()
                if len(excerpt) < 8 or INSTRUCTION_PATTERN.search(excerpt):
                    continue
                if any(anchor not in excerpt.casefold() for anchor in anchors):
                    continue
                overlap = query_terms & terms(excerpt)
                relevance = len(overlap) / max(len(query_terms), 1)
                if len(overlap) < 2 or relevance < self.min_relevance:
                    continue
                ranked.append((relevance, rank, document, excerpt))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        selected: list[Evidence] = []
        counts: dict[str, int] = {}
        seen: set[str] = set()
        for relevance, _, document, excerpt in ranked:
            if excerpt in seen or counts.get(document.source_file, 0) >= 2:
                continue
            evidence = Evidence(
                source_id=f"S{len(selected) + 1}",
                chunk_id=document.chunk_id,
                source_file=document.source_file,
                page_number=document.page_number,
                excerpt=excerpt,
                relevance=relevance,
                tokens=token_count(excerpt),
            )
            if token_count(serialize_evidence([*selected, evidence])) > self.max_tokens:
                continue  # Do not cut a sentence and accidentally remove a negation/condition.
            selected.append(evidence)
            seen.add(excerpt)
            counts[document.source_file] = counts.get(document.source_file, 0) + 1
            if len(selected) >= self.max_sources:
                break
        return CompressionResult(
            evidence=selected,
            original_tokens=original_tokens,
            context_tokens=token_count(serialize_evidence(selected)) if selected else 0,
        )
