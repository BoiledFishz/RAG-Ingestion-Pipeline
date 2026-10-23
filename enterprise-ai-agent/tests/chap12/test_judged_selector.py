"""Round 8: select (Project 1 prompt) then a separate judge call (model stubbed)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from agents.chap12 import factory, tracing
from agents.chap12.judged_selector import JudgedSelector
from models.errors import InvalidEvidence
from models.schemas import Evidence
from models.settings import Settings

EVIDENCE = [Evidence(source_id=f"S{i}", chunk_id=f"c{i}", source_file=f"techqa://d{i}",
                     page_number=1, excerpt=f"excerpt {i}", title=f"t{i}", relevance=0.7,
                     tokens=10) for i in (1, 2, 3)]


class Model:
    def __init__(self, selected: list[str], judge: dict[str, Any] | str) -> None:
        self.selected, self.judge, self.kinds = selected, judge, []  # type: ignore[var-annotated]

    async def generate(self, prompt: str, schema: dict[str, Any]) -> str:
        if prompt.startswith("KIND: ANSWER_JUDGE\n"):
            self.kinds.append("judge")
            return self.judge if isinstance(self.judge, str) else json.dumps(self.judge)
        if prompt.startswith("Audit an already-selected"):
            self.kinds.append("review")
            return json.dumps({"conflict": False, "conflicts": []})
        self.kinds.append("select")
        return json.dumps({"sufficient": bool(self.selected), "source_ids": self.selected})


def judge(decision: str, *rejected: tuple[str, str]) -> dict[str, Any]:
    return {"asked": "a fix for X", "decision": decision,
            "rejected": [{"source_id": s, "rule": r} for s, r in rejected]}


def run(model: Model) -> Any:
    with tracing.recording() as data:
        draft = asyncio.run(JudgedSelector(model).select("Fix for X?", EVIDENCE))
    return draft, data


def test_judge_sees_only_selected_sources_and_keeps_answer() -> None:
    model = Model(["S1"], judge("ANSWER"))
    draft, data = run(model)
    assert [q.source_id for q in draft.quotes] == ["S1"]
    assert model.kinds == ["select", "review", "judge"]
    assert data["selector"]["selected"] == ["S1"] and data["selector"]["decision"] == "ANSWER"


def test_judge_veto_publishes_nothing() -> None:
    draft, data = run(Model(["S1", "S2"], judge("ABSTAIN", ("S1", "J4"), ("S2", "J1"))))
    assert draft.quotes == [] and data["selector"]["decision"] == "ABSTAIN"


def test_partial_veto_keeps_the_other_source() -> None:
    draft, _ = run(Model(["S1", "S2"], judge("ANSWER", ("S2", "J2"))))
    assert [q.source_id for q in draft.quotes] == ["S1"]


def test_decision_follows_the_listed_rejections() -> None:
    draft, data = run(Model(["S1"], judge("ANSWER", ("S1", "J4"))))
    assert draft.quotes == [] and data["selector"]["decision"] == "ABSTAIN"


def test_selector_refusal_skips_the_judge() -> None:
    model = Model([], judge("ANSWER"))
    draft, _ = run(model)
    assert draft.quotes == [] and "judge" not in model.kinds


def test_invalid_judge_output_is_invalid_evidence() -> None:
    with pytest.raises(InvalidEvidence):
        run(Model(["S1"], "not json"))


def test_factory_builds_judged_selector(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHAP12_SELECTOR", "judged")
    monkeypatch.setattr(factory, "TUNED", tmp_path / "absent.json")

    class Spy:
        def __init__(self, *a: object, **k: object) -> None: ...

    monkeypatch.setattr("tools.sample_retriever.SampleRetrieverTool", Spy)
    agent = factory.build_rag_agent(Settings(profile="ollama"), tmp_path / "x.sqlite")
    assert type(agent.selector) is JudgedSelector


def test_judge_can_run_on_another_model() -> None:
    selector_model = Model(["S1"], judge("ANSWER"))
    judge_model = Model([], judge("ABSTAIN", ("S1", "J4")))
    with tracing.recording() as data:
        draft = asyncio.run(JudgedSelector(selector_model, judge_model=judge_model,
                                           judge_name="qwen2.5:14b").select("Q?", EVIDENCE))
    assert draft.quotes == []
    assert "judge" not in selector_model.kinds and judge_model.kinds == ["judge"]
    assert data["selector"]["judge_model"] == "qwen2.5:14b"


def test_factory_uses_judge_model_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHAP12_SELECTOR", "judged")
    monkeypatch.setenv("CHAP12_JUDGE_MODEL", "qwen2.5:14b")
    monkeypatch.setattr(factory, "TUNED", tmp_path / "absent.json")

    class Spy:
        def __init__(self, *a: object, **k: object) -> None: ...

    monkeypatch.setattr("tools.sample_retriever.SampleRetrieverTool", Spy)
    agent = factory.build_rag_agent(Settings(profile="ollama"), tmp_path / "x.sqlite")
    assert agent.selector.judge_name == "qwen2.5:14b"  # type: ignore[attr-defined]
    assert agent.selector.judge_model is not agent.selector.model  # type: ignore[attr-defined]
