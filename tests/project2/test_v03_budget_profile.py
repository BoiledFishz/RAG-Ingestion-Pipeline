from __future__ import annotations
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'enterprise-ai-agent'))
from agents.project2 import budget as module


def test_profile_loader_does_not_accept_missing_or_tampered_evidence(tmp_path):
    assert module.read_frozen_limits(tmp_path) == {'attempts': 16, 'llm_calls': 6, 'seconds': 90}
    target = tmp_path / 'evals/project2-v1/calibration_v03/budget_frozen.json'
    target.parent.mkdir(parents=True)
    target.write_text('{"limits":{"attempts":999,"llm_calls":99,"seconds":999}}', encoding='utf-8')
    with pytest.raises(ValueError):
        module.read_frozen_limits(tmp_path)


def test_budget_blocks_n_plus_one_without_starting():
    budget = module.Budget()
    for _ in range(budget.max_attempts):
        budget.reserve('db')
    with pytest.raises(module.BudgetExceeded, match='dependency_attempt_limit'):
        budget.reserve('db')
    assert budget.attempts == budget.max_attempts
    budget = module.Budget()
    for _ in range(budget.max_llm_calls):
        budget.reserve('llm')
    with pytest.raises(module.BudgetExceeded, match='llm_attempt_limit'):
        budget.reserve('llm')
    assert budget.llm_calls == budget.max_llm_calls
