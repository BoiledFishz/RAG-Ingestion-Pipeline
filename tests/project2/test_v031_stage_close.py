"""Contract metadata only; no invented questions, answers or corpus rows."""
import importlib.util
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))

def module():
    path=ROOT/'scripts/project2_close_stage.py'
    spec=importlib.util.spec_from_file_location('close_stage',path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result

def test_claimed_pass_without_execution_records_cannot_close(tmp_path):
    path=tmp_path/'audit/project2-v1';path.mkdir(parents=True)
    (path/'v031_chap12_gate.json').write_text(json.dumps({'status':'passed','system_gate_executed':True,'gate_scope':'system_gate','checks':[]}),encoding='utf-8')
    assert module().inspect_stage(tmp_path,'ch12')['execution_complete'] is False

def test_repetition_validation_rejects_missing_or_duplicate_registered_slots():
    samples=json.loads((ROOT/'evals/project2-v1/calibration_v031/protocol.json').read_text(encoding='utf-8'))['samples']
    expected={(s['sample_id'],r) for s in samples for r in (1,2,3)}
    rows=[{'sample_id':s,'repeat':r} for s,r in sorted(expected)]
    m=module()
    assert m.repetition_set(rows,'sample_id',expected)
    assert not m.repetition_set(rows[:-1],'sample_id',expected)
    assert not m.repetition_set(rows+[rows[0]],'sample_id',expected)

def test_quality_requires_control_nonregression_and_complete_independent_ratings():
    # Metadata from existing official tune output, without inventing QA content.
    root=ROOT/'evals/project2-v1/ch12/qa-tune'
    tune=json.loads((root/'summary.json').read_text(encoding='utf-8'))
    controls=json.loads((ROOT/'evals/protocol_v0/controls.json').read_text(encoding='utf-8'))
    result=module().quality_acceptance({'tune':tune}, {x['question_id'] for x in controls['records']})
    assert result['acceptance']=='not_accepted'
    assert result['pending_independent_fact_ratings']['tune']==tune['required_facts']['unscored_answer_observations']
    assert any(x['check']=='success_controls_zero_regression' and not x['observed'] for x in result['checks'])
    assert any(x['check']=='independent_required_facts_complete' and not x['observed'] for x in result['checks'])
