"""Round 5: answerability Verifier (model stubbed; no Ollama in tests)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from agents.chap12.budget import BudgetedModel, BudgetLimits
from agents.chap12.contracts import AnalysisRequest
from agents.chap12.db_worker import DatabaseQueryWorker
from agents.chap12.supervisor import Supervisor
from agents.chap12.verifier import AnswerVerifier, verifier_enabled
from models.errors import DependencyUnavailable
from tests.chap12.conftest import context
from tests.chap12.test_critic import QUESTION, FakeRag


class Model:
    def __init__(self, reply: str | Exception) -> None:
        self.reply, self.prompts = reply, []  # type: list[str]

    async def generate(self, prompt: str, schema: dict[str, Any]) -> str:
        self.prompts.append(prompt)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def rag_status(result: Any) -> str:
    return str(next(r for r in result.worker_results if r.worker == "rag").status)


def supervise(sample_index: Path, model: Model, limits: BudgetLimits | None = None,
              verify: bool | None = True) -> Any:
    db = DatabaseQueryWorker(sample_index)
    supervisor = Supervisor({"rag": FakeRag(["swg21996508"]), "database": db}, db.catalog,
                            limits, verifier=AnswerVerifier(BudgetedModel(model)), verify=verify)
    return asyncio.run(supervisor.run(AnalysisRequest(query=QUESTION), context()))


@pytest.fixture(autouse=True)
def no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CHAP12_VERIFIER", raising=False)
    monkeypatch.setenv("CHAP12_CRITIC", "off")


def test_rejected_answer_is_withheld(sample_index: Path) -> None:
    model = Model('{"answers": false}')
    result = supervise(sample_index, model)
    rag = next(r for r in result.worker_results if r.worker == "rag")
    assert rag.status == "no_data" and rag.error.category == "invalid_evidence"
    assert "核验" in " ".join(result.limitations)
    assert QUESTION in model.prompts[0] and "quoted text" in model.prompts[0]
    assert result.usage.llm_calls == 1  # the Verifier call is metered in the request budget


def test_accepted_answer_is_unchanged(sample_index: Path) -> None:
    result = supervise(sample_index, Model('{"answers": true}'))
    assert rag_status(result) == "completed" and result.citations
    assert any(e.node == "verifier" and e.detail == "answers" for e in result.trace)


@pytest.mark.parametrize("reply", ['{"answers": "maybe"}', "not json",
                                   DependencyUnavailable("down")])
def test_undecided_or_failing_model_keeps_answer(sample_index: Path,
                                                 reply: str | Exception) -> None:
    result = supervise(sample_index, Model(reply))
    assert rag_status(result) == "completed"
    assert any(e.node == "verifier" and e.detail == "undecided" for e in result.trace)


def test_exhausted_budget_keeps_answer(sample_index: Path) -> None:
    result = supervise(sample_index, Model('{"answers": false}'),
                       limits=BudgetLimits(max_llm_calls=0))
    assert rag_status(result) == "completed"
    assert any(e.event == "skipped" for e in result.trace)


def test_disabled_by_default_and_env_precedence(sample_index: Path,
                                                monkeypatch: pytest.MonkeyPatch) -> None:
    model = Model('{"answers": false}')
    assert rag_status(supervise(sample_index, model, verify=None)) == "completed"
    assert model.prompts == []
    monkeypatch.setenv("CHAP12_VERIFIER", "off")
    assert rag_status(supervise(sample_index, model)) == "completed" and model.prompts == []
    monkeypatch.setenv("CHAP12_VERIFIER", "on")
    assert verifier_enabled(False) is True
