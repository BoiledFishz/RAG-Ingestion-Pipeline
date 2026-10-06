from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def module():
    spec = importlib.util.spec_from_file_location('v03_calibration', ROOT / 'scripts/project2_v03_calibration.py')
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def test_complete_registered_set_and_all_tune_n_are_frozen():
    registration = module().registration(ROOT)
    assert len(registration['samples']) == 50
    assert len(registration['n_samples']) == 183
    assert registration['repeats'] == 3
    assert registration['paths'] == ['rag_only', 'combination']
    for row in registration['samples'] + registration['n_samples']:
        assert set(row) <= {'sample_id', 'query', 'query_sha256', 'analysis_operation', 'include_samples', 'sample_limit'}
        assert row['query']
    # Keep all original N rows, including three repeated original queries.
    assert len({x['sample_id'] for x in registration['n_samples']}) == 183
    assert len({x['query_sha256'] for x in registration['n_samples']}) == 180


def test_budget_formula_and_fuse_never_select_on_success_subset():
    m = module()
    rows = [{'attempts': 20, 'llm_calls': 4, 'elapsed_seconds': 10, 'censored': False} for _ in range(100)]
    result = m.select_limits(rows)
    assert result['limits'] == {'attempts': 25, 'llm_calls': 5, 'seconds': 15.0}
    rows[0]['censored'] = True
    assert m.select_limits(rows)['status'] == 'incomplete_censored'
    rows = [{'attempts': 33, 'llm_calls': 4, 'elapsed_seconds': 10, 'censored': False} for _ in range(100)]
    assert m.select_limits(rows)['status'] == 'stopped_structural_fuse'
    assert m.select_limits(rows)['limits'] is None


def test_p95_nearest_rank_and_rounding():
    m = module()
    assert m.p95(list(range(1, 101))) == 95
    rows = [{'attempts': 21.1, 'llm_calls': 4.2, 'elapsed_seconds': 10.1, 'censored': False}]
    assert m.select_limits(rows)['limits'] == {'attempts': 28, 'llm_calls': 7, 'seconds': 15.15}
