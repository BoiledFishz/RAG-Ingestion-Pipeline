import asyncio

import pytest
from pydantic import ValidationError
from rag.techqa.data import documents, question_text, questions
from rag.techqa.evidence import answer_passages

from agents.rag_agent.generation import LLMSelector, grounded_response
from models.errors import InvalidEvidence
from models.schemas import Evidence


class SelectionModel:
    def __init__(self, output):
        self.output = output

    async def generate(self, prompt, schema):
        if "ConflictingClaim" in schema.get("$defs", {}):
            return '{"conflict":false,"conflicts":[]}'
        return self.output


def official_passage():
    q = questions("fixture")[0]
    doc = next(d for d in documents("fixture") if d["id"] == q["DOCUMENT"])
    passage = answer_passages(question_text(q), doc["text"], limit=1)[0]
    return question_text(q), [Evidence(
        source_id="S1", chunk_id=f"techqa:{doc['id']}:parent", source_file=f"techqa://{doc['id']}",
        page_number=1, excerpt=passage.text, title=doc["title"], applicability=doc["text"][:500],
        relevance=1, tokens=100,
    )]


def test_id_selection_renders_exact_original_passage():
    query, evidence = official_passage()
    draft = asyncio.run(LLMSelector(SelectionModel(
        '{"sufficient":true,"source_ids":["S1"]}'
    )).select(query, evidence))
    response = grounded_response(draft, evidence)
    assert response.sources[0].quote == evidence[0].excerpt
    assert "setproperty" in response.answer


@pytest.mark.parametrize("output", [
    '{"sufficient":true,"source_ids":["S7"]}',
    '{"sufficient":false,"source_ids":["S1"]}',
    '{"sufficient":"false","source_ids":[]}',
])
def test_unknown_or_inconsistent_selection_is_rejected(output):
    query, evidence = official_passage()
    with pytest.raises((InvalidEvidence, ValidationError)):
        asyncio.run(LLMSelector(SelectionModel(output)).select(query, evidence))


def test_explicit_product_mismatch_blocks_an_initially_selected_answer():
    from models.providers import StructuredModel

    class ReviewRejects:
        def __init__(self):
            self.prompts = []

        async def generate(self, prompt, schema):
            self.prompts.append(prompt)
            return ('{"sufficient":true,"source_ids":["S1"]}' if len(self.prompts) == 1
                    else '{"conflict":true,"conflicts":[{"source_id":"S1",'
                    '"kind":"product","query_claim":"SPSS","source_claim":"Streams"}]}')

    query, evidence = official_passage()
    query = question_text(next(r for r in questions("fixture") if "SPSS" in r["QUESTION_TITLE"]))
    model: StructuredModel = ReviewRejects()
    draft = asyncio.run(LLMSelector(model).select(query, evidence))
    assert draft.quotes == []
    assert len(model.prompts) == 1  # The conflicting product is rejected before another LLM call.


def test_model_cannot_invent_the_grounds_for_rejecting_real_evidence():
    class InventedGrounds:
        def __init__(self):
            self.calls = 0

        async def generate(self, prompt, schema):
            self.calls += 1
            if self.calls == 1:
                return '{"sufficient":true,"source_ids":["S1"]}'
            return ('{"conflict":true,"conflicts":[{"source_id":"S1","kind":"error",'
                    '"query_claim":"08003","source_claim":"forged nonexistent claim"}]}')

    query, evidence = official_passage()
    with pytest.raises(InvalidEvidence, match="actual query/source substrings"):
        asyncio.run(LLMSelector(InventedGrounds()).select(query, evidence))


def test_version_family_and_equivalent_product_names_are_not_conflicts():
    from agents.rag_agent.generation import compatible_versions, same_product_family

    assert compatible_versions("Redhat Linux 7.2", "Redhat Linux 7.x")
    assert not compatible_versions("Redhat Linux 8.2", "Redhat Linux 7.x")
    assert same_product_family("P8 Content Engine", "FileNet Content Engine")
    assert not same_product_family("UrbanCode", "InfoSphere DataStage")


def test_fix_release_is_not_a_product_or_migration_conflict():
    class MislabelledFix:
        async def generate(self, prompt, schema):
            return ('{"conflict":true,"conflicts":[{"source_id":"S1",'
                    '"kind":"product","query_claim":"Streams 4.1.1.1",'
                    '"source_claim":"Streams Version 4.1.1 Fix Pack 4"},'
                    '{"source_id":"S1","kind":"migration",'
                    '"query_claim":"upgrade to 4.1.1.1",'
                    '"source_claim":"Streams Version 4.1.1 Fix Pack 4"}]}')

    query, evidence = official_passage()
    result = asyncio.run(LLMSelector(MislabelledFix()).review(query, evidence))
    assert result.sufficient and result.source_ids == ["S1"]


def test_real_installation_question_cannot_use_rollback_fault_remedy():
    from agents.rag_agent.generation import explicit_mismatch

    row = next(r for r in questions("regression") if r["QUESTION_ID"] == "DEV_Q000")
    doc = next(d for d in documents("regression") if d["id"] == "swg21960632")
    source = Evidence(source_id="S1", chunk_id=f"techqa:{doc['id']}:parent",
                      source_file=f"techqa://{doc['id']}", page_number=1, title=doc["title"],
                      applicability=doc["text"][:500], excerpt=doc["text"],
                      relevance=1, tokens=100)
    assert explicit_mismatch(question_text(row), source)
    # The original rollback premise remains compatible with its own remedy.
    assert not explicit_mismatch(doc["text"].split("CAUSE")[0], source)
    query, supported = official_passage()
    assert not explicit_mismatch(query, supported[0])


def test_socket_component_check_preserves_correct_gateway_source():
    from rag.techqa.query import component_conflict

    row = next(r for r in questions("regression") if r["QUESTION_ID"] == "DEV_Q007")
    docs = {d["id"]: d for d in documents("regression")}
    assert component_conflict(question_text(row), docs["swg21970417"]["title"])
    assert not component_conflict(question_text(row), docs["swg21625776"]["title"])
