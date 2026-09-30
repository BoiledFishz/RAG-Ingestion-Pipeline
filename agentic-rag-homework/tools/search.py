from __future__ import annotations

import re

from models.schemas import Document


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9_.:/-]*|[\u4e00-\u9fff]+", text.casefold()))


class SearchTool:
    """Offline search adapter. A production web API can replace this implementation."""

    name = "search"
    description = "Search an external document collection when internal RAG is insufficient."

    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents

    async def invoke(self, query: str, limit: int = 5) -> list[Document]:
        query_words = words(query)
        ranked = sorted(
            self.documents,
            key=lambda doc: len(query_words & words(doc.title + " " + doc.text)),
            reverse=True,
        )
        return [
            doc.model_copy(
                update={
                    "score": len(query_words & words(doc.title + " " + doc.text))
                    / max(len(query_words), 1)
                }
            )
            for doc in ranked
            if query_words & words(doc.title + " " + doc.text)
        ][:limit]
