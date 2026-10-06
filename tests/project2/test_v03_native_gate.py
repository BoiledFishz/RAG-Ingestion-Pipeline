import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def loader():
    spec = importlib.util.spec_from_file_location('gate_v03', ROOT / 'scripts/run_project2_v03_gate.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def result():
    return {'run_id': 'unique', 'status': 'partial', 'usage': {'attempts': 14, 'llm_calls': 3},
            'workers': {'rag': {'run_id': 'unique', 'status': 'completed', 'payload': {'trace': {'original_query': 'original'}}, 'evidence': [{'source_id': 'S1'}], 'error': None},
                        'database': {'run_id': 'unique', 'status': 'no_data', 'payload': {'measurement_complete': True, 'groups': [{'count': 0}]}, 'error': None}}}


def test_status_gate_cannot_claim_refusal_quality():
    m = loader()
    check = m.check_consistency(result(), m.read_matrix(ROOT))
    assert check['passed']
    assert check['rag_status'] == 'completed'
    assert 'quality_passed' not in check
    bad = result(); bad['status'] = 'completed'
    assert not m.check_consistency(bad, m.read_matrix(ROOT))['passed']


def test_nontraceable_result_fails():
    m = loader(); bad = result(); bad['workers']['rag']['run_id'] = 'other'
    assert not m.check_consistency(bad, m.read_matrix(ROOT))['passed']
    bad = result(); bad['workers']['rag']['payload'] = {}
    assert not m.check_consistency(bad, m.read_matrix(ROOT))['passed']
