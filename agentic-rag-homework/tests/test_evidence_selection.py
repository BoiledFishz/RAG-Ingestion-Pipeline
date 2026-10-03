import asyncio

import pytest
from rag.techqa.data import documents, question_text, questions

from agents.rag_agent.service import GroundedAnswerer
from models.errors import ModelUnavailable
from models.llm import ScriptedModel
from models.schemas import Document


def official_evidence():
    row = questions("fixture")[0]
    doc = next(d for d in documents("fixture") if d["id"] == row["DOCUMENT"])
    return question_text(row), [Document(
        document_id=doc["id"], title=doc["title"], text=doc["text"],
        source=f"techqa://{doc['id']}", score=1,
    )]


@pytest.mark.parametrize("invalid", [
    {"sufficient": True, "selected": [999]},
    {"sufficient": "true", "selected": [1]},
    {"sufficient": True, "selected": []},
    {"sufficient": False, "selected": [1]},
    {"sufficient": True, "selected": [True]},
])
def test_invalid_selection_never_becomes_an_answer(invalid):
    query, docs = official_evidence()
    model = ScriptedModel([invalid, invalid])
    response = asyncio.run(GroundedAnswerer(model).answer(query, docs))
    assert len(model.prompts) == 2
    assert not response.sources and response.confidence == 0


def test_selected_passage_preserves_solution_and_provenance():
    query, docs = official_evidence()
    response = asyncio.run(GroundedAnswerer(
        ScriptedModel([{"sufficient": True, "selected": [1]}])
    ).answer(query, docs))
    assert "setproperty" in response.answer
    assert "RELATED INFORMATION" not in response.answer
    assert len(response.answer) < 1000
    assert response.sources[0].quote in docs[0].text
    assert response.sources[0].document_id == docs[0].document_id


def test_model_outage_is_not_a_knowledge_base_refusal():
    query, docs = official_evidence()
    with pytest.raises(ModelUnavailable):
        asyncio.run(GroundedAnswerer(ScriptedModel([])).answer(query, docs))


def test_named_cve_cannot_be_answered_from_an_unrelated_real_technote():
    from agents.rag_agent.service import REFUSAL

    _, unrelated_docs = official_evidence()
    question = next(q for q in questions("fixture") if "CVE-2017-3156" in q["QUESTION_TITLE"])
    model = ScriptedModel([])
    response = asyncio.run(GroundedAnswerer(model).answer(question_text(question), unrelated_docs))
    assert response.answer == REFUSAL and response.sources == []
    assert model.prompts == []


def test_incidental_background_error_does_not_exclude_a_real_documented_workaround():
    query, docs = official_evidence()
    # The original question reports SQL state 08003 in its background; its main
    # request concerns environment inheritance, which the documented command answers.
    model = ScriptedModel([{"sufficient": True, "selected": [1]}])
    response = asyncio.run(GroundedAnswerer(model).answer(query, docs))
    assert response.sources and "streamtool setproperty" in response.answer
