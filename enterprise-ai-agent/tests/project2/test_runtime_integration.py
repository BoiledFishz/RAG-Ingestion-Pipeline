"""Actual subprocess stop/restart; never an evaluation --resume substitute."""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'scripts'))


def test_process_restart_resume():
    from run_project2_ch13_gate import REQUIRED
    from summarize_project2 import stage_verdict
    # Ordinary pytest validates immutable real restart evidence. It cannot
    # overwrite or consume a new stage gate, model request or repair round.
    report=json.loads((ROOT/'audit/project2-v1/ch13_v033_round0/gate.json').read_text(encoding='utf-8'))
    assert report['status']=='passed', report['failure_items']
    assert report['system_gate_executed'] is True
    assert {x['check'] for x in report['checks']}==set(REQUIRED)
    assert stage_verdict(report)=='passed'
    assert all((ROOT/x['evidence_file']).is_file() for x in report['checks'])
