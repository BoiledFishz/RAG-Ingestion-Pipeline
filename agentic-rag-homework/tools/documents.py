from __future__ import annotations

from models.schemas import Document


class DocumentRetrievalTool:
    name = "read_document"
    description = "Read a full document selected from a search result."

    def __init__(self, documents: list[Document]) -> None:
        self.documents = {document.document_id: document for document in documents}

    async def invoke(self, document_id: str) -> Document | None:
        return self.documents.get(document_id)
