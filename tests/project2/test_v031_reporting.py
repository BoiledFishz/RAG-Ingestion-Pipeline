"""Counts and summaries must be derived from files, never entered by hand."""
import importlib.util
import sys
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))

def load():
    spec=importlib.util.spec_from_file_location('p2_report',ROOT/'scripts/project2_v031_report.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_prior_batch_count_and_censor_are_read_from_immutable_records():
    m=load();folder=ROOT/'evals/project2-v1/calibration_v03'
    rows=[json.loads(x) for x in (folder/'requests.jsonl').read_text(encoding='utf-8').splitlines()]
    batch=m.old_batch(folder)
    assert batch['requests']==len(rows) and not batch['used_for_decision']
    assert str(round(max(x['elapsed_seconds'] for x in rows if x['censored']),3)) in batch['censor_reason']

def test_comparison_rendering_is_compact_and_contains_ci_and_declines():
    m=load()
    value={'new_version':{'complete':{'numerator':9,'denominator':12,'mean':.75,'ci95':[.4,.9]}},'regression_items':[{'sample_id':'an official query'}]}
    text=m.comparison_text(value)
    assert '9/12' in text and '95%CI' in text and '1' in text
    assert len(text)<500

def test_qa_report_keeps_repeats_ci_and_unscored_answers_visible():
    # Only existing official-data measurements; no synthetic QA.
    m=load()
    summary=json.loads((ROOT/'evals/project2-v1/ch12/qa-tune/summary.json').read_text(encoding='utf-8'))
    result=m.qa_text(summary)
    assert '21/60' in result and '95%CI' in result and '范围' in result
    assert str(summary['required_facts']['unscored_answer_observations']) in result
    assert '待独立评分' in result and '条件子集' in result

def test_unsupported_business_comparison_does_not_call_incomplete_tasks_regressions():
    value=json.loads((ROOT/'evals/project2-v1/ch12/summary.json').read_text(encoding='utf-8'))
    result=load().comparison_text(value)
    assert '未完整完成' in result and '退化项' not in result

def test_completed_measurements_do_not_override_frozen_quality_requirements():
    m=load()
    import sys
    sys.path.insert(0,str(ROOT/'scripts'))
    from project2_close_stage import quality_acceptance
    tune=json.loads((ROOT/'evals/project2-v1/ch12/qa-tune/summary.json').read_text(encoding='utf-8'))
    controls=json.loads((ROOT/'evals/protocol_v0/controls.json').read_text(encoding='utf-8'))
    receipt={'execution_complete':True,'quality':quality_acceptance({'tune':tune},{x['question_id'] for x in controls['records']})}
    result=m.stage_progression(receipt)
    assert result['status']=='stopped_s14_acceptance'
    assert 'S14' in result['reason'] and 'held-out' in result['reason']
    assert receipt['execution_complete'] is True

def test_gate_evidence_binding_updates_partial_coverage_without_inventing_passes():
    import csv
    import copy
    m=load();docs=ROOT/'specs/project2/v0.3.1'
    approved=list(csv.DictReader((docs/'traceability.csv').open(encoding='utf-8-sig',newline='')))
    items=json.loads((ROOT/'audit/project2-v1/traceability_runtime.json').read_text(encoding='utf-8'))['items']
    gate=json.loads((ROOT/'audit/project2-v1/v031_chap12_gate.json').read_text(encoding='utf-8'))
    bound=m.bind_gate_partial_evidence(ROOT,approved,copy.deepcopy(items),gate)
    assert sum(x['execution_status']=='部分' for x in bound)>=sum(x['execution_status']=='部分' for x in items)
    assert not any(x['execution_status']=='通过' for x in bound)
    assert any(y.get('gate_check')=='AC12-01' for x in bound for y in x['partial_evidence'])
    failed={**gate,'status':'failed','system_gate_executed':False}
    assert m.bind_gate_partial_evidence(ROOT,approved,copy.deepcopy(items),failed)==items
