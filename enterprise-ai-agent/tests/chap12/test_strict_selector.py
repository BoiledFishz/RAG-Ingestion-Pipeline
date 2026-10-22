"""Round 7: strict answerability selector (model stubbed)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from agents.chap12 import factory, tracing
from agents.chap12.strict_selector import StrictSelector, selector_mode
from agents.rag_agent.generation import LLMSelector
from models.errors import InvalidEvidence
from models.schemas import Evidence
from models.settings import Settings

EVIDENCE = [Evidence(source_id=f"S{i}", chunk_id=f"c{i}", source_file=f"techqa://d{i}",
                     page_number=1, excerpt=f"excerpt {i} applies to Windows", title=f"t{i}", relevance=0.7,
                     tokens=10) for i in (1, 2)]


class Model:
    def __init__(self, selection: dict[str, Any], conflict: bool = False) -> None:
        self.selection, self.conflict, self.prompts = selection, conflict, []  # type: ignore[var-annotated]

    async def generate(self, prompt: str, schema: dict[str, Any]) -> str:
        self.prompts.append(prompt)
        if prompt.startswith("KIND: ANSWERABILITY_SELECT\n"):
            return json.dumps(self.selection)
        if self.conflict:
            return json.dumps({"conflict": True, "conflicts": [{
                "source_id": "S1", "kind": "platform", "query_claim": "AIX",
                "source_claim": "Windows"}]})
        return json.dumps({"conflict": False, "conflicts": []})


def run(model: Model, query: str = "Fix for X on AIX?") -> Any:
    with tracing.recording() as data:
        draft = asyncio.run(StrictSelector(model).select(query, EVIDENCE))
    return draft, data


def test_refusal_rules_come_first_and_reasons_are_traced() -> None:
    model = Model({"asked": "fix for X", "rejected": [{"source_id": "S1", "rule": "R5"},
                                                     {"source_id": "S2", "rule": "R1"}],
                   "sufficient": False, "source_ids": []})
    draft, data = run(model)
    prompt = model.prompts[0]
    assert draft.quotes == [] and len(model.prompts) == 1  # no review when refusing
    assert prompt.index("REJECT rules") < prompt.index("STEP 3") < prompt.index("QUESTION:")
    assert data["selector"]["rejected"][0] == {"source_id": "S1", "rule": "R5"}


def test_selected_source_goes_through_inherited_review() -> None:
    model = Model({"asked": "fix", "rejected": [{"source_id": "S2", "rule": "R2"}],
                   "sufficient": True, "source_ids": ["S1"]})
    draft, _ = run(model)
    assert [q.source_id for q in draft.quotes] == ["S1"] and len(model.prompts) == 2


def test_explicit_conflict_review_still_rejects() -> None:
    model = Model({"asked": "fix", "rejected": [], "sufficient": True, "source_ids": ["S1"]},
                  conflict=True)
    draft, _ = run(model, query="Fix for X on AIX?")
    assert draft.quotes == []


@pytest.mark.parametrize("selection", [
    {"asked": "a", "rejected": [], "sufficient": True, "source_ids": []},
    {"asked": "a", "rejected": [{"source_id": "S1", "rule": "R1"}], "sufficient": True,
     "source_ids": ["S1"]},
    {"asked": "a", "rejected": [], "sufficient": False, "source_ids": ["S9"]},
])
def test_inconsistent_output_is_invalid_evidence(selection: dict[str, Any]) -> None:
    with pytest.raises(InvalidEvidence):
        run(Model(selection))


def test_selector_choice(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CHAP12_SELECTOR", raising=False)
    assert selector_mode(None) == "project1" and selector_mode("strict") == "strict"
    monkeypatch.setenv("CHAP12_SELECTOR", "project1")
    assert selector_mode("strict") == "project1"
    path = tmp_path / "real_config.json"
    path.write_text(json.dumps({"adopted": {"selector": "strict"}}))
    monkeypatch.setattr(factory, "TUNED", path)
    monkeypatch.delenv("CHAP12_SELECTOR", raising=False)

    class Spy:
        def __init__(self, *a: object, **k: object) -> None: ...

    monkeypatch.setattr("tools.sample_retriever.SampleRetrieverTool", Spy)
    tuned = factory.build_rag_agent(Settings(profile="ollama"), tmp_path / "x.sqlite")
    p1 = factory.build_rag_agent(Settings(profile="ollama"), tmp_path / "x.sqlite", tuned=False)
    assert type(tuned.selector) is StrictSelector and type(p1.selector) is LLMSelector
