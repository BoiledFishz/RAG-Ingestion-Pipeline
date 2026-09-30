"""Small real cosine vector index for a self-contained homework demo."""

from __future__ import annotations

import hashlib
import math
import re

from models.schemas import Document


def embed(text: str, dimensions: int = 256) -> list[float]:
    vector = [0.0] * dimensions
    for word in re.findall(r"[a-z0-9][a-z0-9_.:/-]*|[\u4e00-\u9fff]+", text.casefold()):
        digest = hashlib.sha256(word.encode()).digest()
        vector[int.from_bytes(digest[:4], "big") % dimensions] += 1
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


class MemoryVectorStore:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents
        self.vectors = {doc.document_id: embed(doc.title + " " + doc.text) for doc in documents}

    async def search(self, query: str, top_k: int) -> list[Document]:
        query_vector = embed(query)
        ranked = sorted(
            self.documents,
            key=lambda doc: sum(
                left * right
                for left, right in zip(query_vector, self.vectors[doc.document_id], strict=True)
            ),
            reverse=True,
        )
        output: list[Document] = []
        for doc in ranked[:top_k]:
            score = sum(
                left * right
                for left, right in zip(query_vector, self.vectors[doc.document_id], strict=True)
            )
            output.append(doc.model_copy(update={"score": round(score, 4)}))
        return output
