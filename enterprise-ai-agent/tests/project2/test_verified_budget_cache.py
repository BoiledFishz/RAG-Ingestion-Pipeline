"""Immutable server configuration must not consume every request deadline."""
import os
import pytest
from agents.project2 import budget

@pytest.mark.skipif(os.name != 'nt', reason='Windows sharing semantics')
def test_verified_source_is_locked_against_rewrite(tmp_path):
    from agents.project2.budget_cache import ReadLocks
    path=tmp_path/'frozen.json';path.write_text('{}',encoding='utf-8')
    with ReadLocks([path]):
        with pytest.raises(PermissionError):path.write_text('changed',encoding='utf-8')
        assert path.read_text(encoding='utf-8')=='{}'
    path.write_text('released',encoding='utf-8')

@pytest.mark.skipif(os.name != 'nt', reason='Windows immutable configuration snapshot')
def test_request_uses_preverified_locked_limits(monkeypatch):
    budget.prepare_budget_configuration()
    def repeated_verification():
        raise AssertionError('Request repeated full frozen evidence hashing')
    monkeypatch.setattr(budget,'read_frozen_limits',repeated_verification)
    instance=budget.Budget(seconds=.05)
    assert instance.remaining()>0
    assert instance.max_attempts==19 and instance.max_llm_calls==6
