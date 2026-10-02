"""Enterprise adapter to the shared full-corpus TechQA retrieval pipeline."""

from __future__ import annotations

from rag.techqa.retrieval import TechQAParentResolver, build_pipeline, open_index
from rag.techqa.settings import acceptance_score

from models.schemas import Document, RetrieverInput
from tools.retriever import RetrieverTool


class TechQARetrieverTool(RetrieverTool):
    def __init__(self) -> None:
        self.pipeline = build_pipeline(final_k=10)
        self.parents = TechQAParentResolver(open_index())

    async def invoke(self, request: RetrieverInput) -> list[Document]:
        filters = self.secure_filters(request.filters)
        outcome = await self.pipeline.retrieve(request.query, mode="hybrid", filters=filters)
        parents = await self.parents.retrieve_by_chunk_ids(
            [str(r.metadata["parent_id"]) for r in outcome.results if r.metadata.get("parent_id")]
        )
        by_id = {p.chunk_id: p for p in parents}
        expanded, seen = [], set()
        for result in outcome.results:
            parent = by_id.get(str(result.metadata.get("parent_id")))
            if parent and parent.chunk_id not in seen:
                from dataclasses import replace

                score, threshold = acceptance_score(
                    request.query,
                    result.text,
                    result.score,
                    fallback=outcome.diagnostics.reranker_fallback,
                )

                expanded.append(
                    replace(
                        parent,
                        score=score,
                        metadata={
                            **parent.metadata,
                            "_full_parent": True,
                            "_acceptance_threshold": threshold,
                        },
                    )
                )
                seen.add(parent.chunk_id)
        return [
            Document(
                chunk_id=r.chunk_id,
                text=r.text,
                source_file=r.source_file,
                page_number=r.page_number,
                score=r.score,
                metadata=r.metadata,
            )
            for r in expanded[: request.top_k]
        ]
