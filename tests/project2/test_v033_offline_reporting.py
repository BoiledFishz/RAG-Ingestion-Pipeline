"""Offline evidence checks; no inference or held-out body diagnosis."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))


def test_incomplete_confirmation_cannot_create_a_blind_package(tmp_path, monkeypatch):
    import export_project2_v033_blind as exporter

    monkeypatch.setattr(exporter, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='Final confirmatory run incomplete'):
        exporter.build()
    assert not (tmp_path / 'evals/project2-v1/blind_review_v033_final').exists()


def test_summary_records_the_three_comparisons_without_inventing_missing_results():
    import json
    from project2_v033_report import generate

    generate(ROOT)
    report = json.loads((ROOT / 'audit/project2-v1/summary.json').read_text(encoding='utf-8'))
    assert len(report['comparisons']) == 3
    for comparison in report['comparisons']:
        if comparison['summary'] is None:
            assert comparison['status'] == '未执行'
            assert comparison['evidence_file'] is None
        else:
            assert comparison['source_sha256']
            assert (ROOT / comparison['evidence_file']).is_file()


def test_current_chap13_trace_evidence_is_classified_check_by_check():
    import json
    from project2_v033_report import generate

    generate(ROOT)
    runtime = json.loads((ROOT / 'audit/project2-v1/traceability_runtime.json').read_text(encoding='utf-8'))
    proofs = [proof for item in runtime['items'] for proof in item.get('partial_evidence', [])
              if proof['evidence_file'].startswith('audit/project2-v1/ch13_v033_')]
    assert proofs
    for proof in proofs:
        assert {item['check'] for item in proof['check_evidence']} == set(proof['gate_check'])
        assert all(item['evidence_type'] in {'真实运行', '故障注入', '契约测试(Mock)'}
                   for item in proof['check_evidence'])
        assert all((ROOT / item['evidence_file']).is_file() for item in proof['check_evidence'])


def test_container_startup_failure_is_reported_as_a_prerequisite_failure():
    import json
    from project2_v033_report import generate

    generate(ROOT)
    report = json.loads((ROOT / 'audit/project2-v1/summary.json').read_text(encoding='utf-8'))
    observed = json.loads((ROOT / 'audit/project2-v1/container_feasibility_after_start.json').read_text(encoding='utf-8'))
    chapter = next(item for item in report['stages'] if item['stage'] == 'Chap14')
    assert chapter['status'] == 'blocked'
    assert chapter['gate_status'] == 'not_run'
    assert report['stop_reason'] == observed['reason']
    assert report['container_feasibility']['container_gate_executed'] is False
