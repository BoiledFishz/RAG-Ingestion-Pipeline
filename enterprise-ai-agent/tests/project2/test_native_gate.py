"""Native end-to-end gate; successful DB alone must not count as completed."""

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_approved_native_gate_preserves_failed_no_answer_quality_record() -> None:
    # v03 explicitly replaced AC12-23 with state-consistency(a) and quality(b).
    # The old failed native gate is retained, never relabelled as a success.
    old=json.loads((ROOT/'audit/project2-v1/native_gate_round2.json').read_text(encoding='utf-8'))
    assert old['status']=='failed' and 'AC12-23' in old['failure_items']
    report=json.loads((ROOT/'audit/project2-v1/v031_native_gate_round1.json').read_text(encoding='utf-8'))
    assert report["status"] == "passed", report["failure_items"]
    assert all(x['observed']==x['expected'] and x['status']=='passed' for x in report['checks'])
    assert {'AC12-01','AC12-23(a)'}=={x['check'] for x in report['checks']}
    assert report['n_quality']['metric_is_gate'] is False
    assert report['n_quality']['numerator'] < report['n_quality']['denominator']
    assert report['n_quality']['project2_claims_quality_improvement'] is False
