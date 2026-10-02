"""Query rewrite -> vector tool -> compression -> grounded structured response."""

from __future__ import annotations

import re
from typing import Protocol

from rag.techqa.index import tokens

from models.llm import StructuredModel
from models.schemas import Document, RAGResponse, RewriteDecision, Source
from tools.retriever import RetrieverTool

REFUSAL = "知识库中没有足够信息回答该问题。"
CLARIFY = "请补充具体服务、操作和错误信息。"
STOPWORDS = {"a", "an", "and", "are", "how", "is", "of", "the", "to", "what", "why"}


def terms(text: str) -> set[str]:
    text = re.sub(r"\btime(?:s)?\s+out\b", "timeout", text, flags=re.IGNORECASE)
    return {
        word
        for word in re.findall(r"[a-z0-9][a-z0-9_.:/-]*|[\u4e00-\u9fff]+", text.casefold())
        if word not in STOPWORDS
    }


class Rewriter(Protocol):
    async def rewrite(self, query: str) -> RewriteDecision: ...


class RuleRewriter:
    async def rewrite(self, query: str) -> RewriteDecision:
        normalized = " ".join(query.split())
        vague = normalized.casefold() in {"help", "it is broken", "权限有问题", "帮我看看"}
        if vague:
            return RewriteDecision(
                rewritten_query=normalized, action="clarify", clarification=CLARIFY
            )
        rewritten = re.sub(r"\btimes out\b", "timeout", normalized, flags=re.IGNORECASE)
        return RewriteDecision(rewritten_query=rewritten, action="retrieve")


class LLMRewriter:
    def __init__(self, model: StructuredModel) -> None:
        self.model = model

    async def rewrite(self, query: str) -> RewriteDecision:
        prompt = (
            "Rewrite for retrieval without answering or inventing facts. Preserve names, codes, "
            "numbers and negations. If too vague, ask one clarification. Return only JSON.\n"
            f"SCHEMA: {RewriteDecision.model_json_schema()}\nQUERY: {query!r}"
        )
        return RewriteDecision.model_validate_json(
            await self.model.generate(prompt, RewriteDecision.model_json_schema())
        )


class ContextCompressor:
    def __init__(self, max_sources: int = 4) -> None:
        self.max_sources = max_sources

    def compress(self, query: str, documents: list[Document]) -> list[tuple[Document, str, float]]:
        query_terms = terms(query)
        selected: list[tuple[Document, str, float]] = []
        for document in documents:
            if document.source.startswith("techqa://"):
                query_words = set(tokens(query))
                overlap = len(
                    query_words & set(tokens(document.title + " " + document.text))
                ) / max(len(query_words), 1)
                if overlap < 0.5:
                    continue
                # Keep the resolution and its conditions together, copied verbatim from IBM.
                match = re.search(
                    r"(?:RESOLVING THE PROBLEM|Problem Solution|ANSWER)\s*\n",
                    document.text,
                    flags=re.I,
                )
                text = document.text[match.end() :] if match else document.text
                paragraphs = re.split(r"\n\s*\n", text)
                excerpt = ""
                for paragraph in paragraphs:
                    if len(excerpt) + len(paragraph) > 2600:
                        break
                    excerpt += ("\n\n" if excerpt else "") + paragraph
                if excerpt.strip():
                    selected.append((document, excerpt.strip(), overlap))
                continue
            sentences = re.split(r"(?<=[.!?。！？])\s+", document.text)
            best = max(
                sentences,
                key=lambda sentence: len(query_terms & terms(sentence)),
                default="",
            )
            overlap = len(query_terms & terms(best)) / max(len(query_terms), 1)
            if best and overlap >= 0.34:
                selected.append((document, best.strip(), overlap))
        selected.sort(key=lambda item: (item[2], item[0].score), reverse=True)
        return selected[: self.max_sources]


class RAGAgent:
    def __init__(self, rewriter: Rewriter, retriever: RetrieverTool) -> None:
        self.rewriter, self.retriever = rewriter, retriever
        self.compressor = ContextCompressor()

    async def run(self, query: str) -> RAGResponse:
        decision = await self.rewriter.rewrite(query)
        if decision.action == "clarify":
            return RAGResponse(answer=decision.clarification, sources=[], confidence=0)
        candidates = await self.retriever.invoke(decision.rewritten_query)
        evidence = self.compressor.compress(decision.rewritten_query, candidates)
        if not evidence:
            return RAGResponse(answer=REFUSAL, sources=[], confidence=0)
        sources = [
            Source(document_id=doc.document_id, source=doc.source, quote=sentence)
            for doc, sentence, _ in evidence[:2]
        ]
        answer = "\n".join(f"{source.quote} [{index}]" for index, source in enumerate(sources, 1))
        confidence = round(min(0.95, 0.3 + sum(item[2] for item in evidence[:2]) / 3), 3)
        return RAGResponse(answer=answer, sources=sources, confidence=confidence)
