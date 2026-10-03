from __future__ import annotations

import asyncio

import pytest

from agents.rag_agent.generation import grounded_response
from agents.rag_agent.service import RAGAgent
from models.errors import InvalidEvidence
from models.schemas import Evidence, QueryRequest, Quotation, SelectionDraft
from vectorstore.qdrant import QdrantStore


def test_agent_answers_known_question_with_structured_sources(
    agent_bundle: tuple[RAGAgent, QdrantStore],
) -> None:
    agent, _ = agent_bundle
    run = asyncio.run(
        agent.run(
            QueryRequest(
                query="How are Streams environment variables set after upgrade to 4.1.1.2?"
            )
        )
    )
    assert run.trace.status == "answered"
    assert "streamtool" in run.response.answer
    assert run.response.sources and 0 < run.response.confidence <= 1
    assert set(run.response.model_dump()) == {"answer", "sources", "confidence"}


def test_agent_unknown_refusal_skips_generation(
    agent_bundle: tuple[RAGAgent, QdrantStore],
) -> None:
    class MustNotRun:
        async def select(
            self,
            query: str,
            evidence: list[Evidence],
            correction: str = "",
        ) -> SelectionDraft:
            raise AssertionError("generation must not run")

    agent, _ = agent_bundle
    agent.selector = MustNotRun()
    run = asyncio.run(agent.run(QueryRequest(query="How do I repair PostgreSQL XX999?")))
    assert run.trace.status == "unanswerable"
    assert run.response.sources == [] and run.response.confidence == 0


def test_agent_ambiguity_does_not_call_retriever(
    agent_bundle: tuple[RAGAgent, QdrantStore],
) -> None:
    agent, _ = agent_bundle
    run = asyncio.run(agent.run(QueryRequest(query="权限有问题，怎么办？")))
    assert run.trace.status == "clarified"
    assert not run.trace.tool_called
    assert not run.response.sources


class HallucinatingSelector:
    def __init__(self, invalid_id: bool) -> None:
        self.calls = 0
        self.invalid_id = invalid_id

    async def select(
        self,
        query: str,
        evidence: list[Evidence],
        correction: str = "",
    ) -> SelectionDraft:
        self.calls += 1
        return SelectionDraft(
            quotes=[
                Quotation(
                    source_id="S99" if self.invalid_id else evidence[0].source_id,
                    quote=evidence[0].excerpt
                    if self.invalid_id
                    else "WebSphere ADMU0111E guarantees a memory leak.",
                )
            ]
        )


@pytest.mark.parametrize("invalid_id", [True, False])
def test_fabricated_id_or_claim_retried_once_then_rejected(
    agent_bundle: tuple[RAGAgent, QdrantStore],
    invalid_id: bool,
) -> None:
    agent, _ = agent_bundle
    bad = HallucinatingSelector(invalid_id)
    agent.selector = bad
    run = asyncio.run(
        agent.run(
            QueryRequest(
                query="How are Streams environment variables set after upgrade to 4.1.1.2?"
            )
        )
    )
    assert run.trace.status == "invalid_evidence"
    assert bad.calls == 2
    assert run.response.sources == [] and run.response.confidence == 0


def test_model_cannot_omit_negation_from_a_quote() -> None:
    evidence = Evidence(
        source_id="S1",
        chunk_id="x",
        source_file="x.md",
        page_number=1,
        excerpt="Reserved concurrency does not pre-initialize environments.",
        relevance=1,
        tokens=8,
    )
    with pytest.raises(InvalidEvidence):
        grounded_response(
            SelectionDraft(
                quotes=[
                    Quotation(
                        source_id="S1",
                        quote="Reserved concurrency does pre-initialize environments.",
                    )
                ]
            ),
            [evidence],
        )


def test_retry_receives_precise_validation_error_and_keeps_failure_trace(
    agent_bundle: tuple[RAGAgent, QdrantStore],
) -> None:
    class RepairingSelector:
        def __init__(self) -> None:
            self.corrections: list[str] = []

        async def select(self, query: str, evidence: list[Evidence],
                         correction: str = "") -> SelectionDraft:
            self.corrections.append(correction)
            if not correction:
                raise InvalidEvidence("source_claim is absent from S1; copy an exact source span")
            return SelectionDraft(quotes=[Quotation(source_id=evidence[0].source_id,
                                                  quote=evidence[0].excerpt)])

    from rag.techqa.data import documents, question_text, questions

    from models.schemas import Document

    agent, _ = agent_bundle
    row = questions("fixture")[0]
    doc = next(d for d in documents("fixture") if d["id"] == row["DOCUMENT"])

    async def retrieve_original(request):
        return [Document(chunk_id=f"techqa:{doc['id']}:parent", text=doc["text"],
                         source_file=f"techqa://{doc['id']}", score=1,
                         metadata={"_full_parent": True, "title": doc["title"]})]

    agent.retriever.invoke = retrieve_original
    selector = RepairingSelector()
    agent.selector = selector
    run = asyncio.run(agent.run(QueryRequest(query=question_text(questions("fixture")[0]))))
    assert run.trace.status == "answered" and run.trace.retries == 1
    assert len(selector.corrections) == 2
    assert "source_claim is absent from S1" in selector.corrections[1]
    assert "Allowed source IDs: S1" in selector.corrections[1]
    assert run.trace.validation_failures == [
        "source_claim is absent from S1; copy an exact source span",
    ]
