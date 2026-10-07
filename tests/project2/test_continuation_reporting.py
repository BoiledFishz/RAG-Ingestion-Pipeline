"""Reporting never turns the S14 exception into a quality pass."""
import importlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))


def test_continuation_authority_is_hash_checked_and_does_not_waive_s14():
    from project2_continuation_report import authority
    receipt=authority(ROOT)
    assert receipt['continue_ch13_ch14_ch15_with_s14_failed'] and not receipt['s14_waived']


def test_all_six_states_account_for_all_real_combined_observations():
    from project2_continuation_report import state_counts,STATES
    result=state_counts(ROOT/'evals/project2-v1/ch12/business.requests.jsonl')
    assert set(result['counts'])==set(STATES)
    assert result['denominator']==sum(result['counts'].values())==150
    summary=json.loads((ROOT/'evals/project2-v1/ch12/summary.json').read_text(encoding='utf-8'))
    other=summary['requests']-summary['new_version']['complete']['numerator']-summary['new_version']['partial']['numerator']
    assert sum(result['counts'][k] for k in ('no_data','permission_denied','timeout','failed'))==other


def test_gate_requires_each_registered_boolean_not_a_claimed_pass():
    from run_project2_ch13_gate import REQUIRED
    from summarize_project2 import stage_verdict
    report={'status':'passed','system_gate_executed':True,'gate_scope':'system_gate',
            'checks':[{'check':x,'observed':True,'expected':True,'status':'passed'} for x in REQUIRED]}
    assert stage_verdict(report)=='passed'
    report['checks'][0]['observed']=False
    assert stage_verdict(report)=='failed'
def test_runtime_binding_requires_immutable_passing_gate_and_never_claims_whole_requirement(tmp_path):
    from project2_continuation_report import bind_runtime_stage_evidence
    approved=[{'requirement_id':'runtime-contract','scenario_ids':'AC13-01'}]
    items=[{'requirement_id':'runtime-contract','execution_status':'待实施','evidence_files':[]}]
    gate={'stage':'Chap13','status':'passed','repair_rounds':0,'system_gate_executed':True,'gate_scope':'system_gate',
          'checks':[{'check':'same_run_id','expected':True,'observed':True,'status':'passed'}]}
    folder=tmp_path/'audit/project2-v1/ch13_round0';folder.mkdir(parents=True)
    (folder/'gate.json').write_text(json.dumps(gate),encoding='utf-8')
    result=bind_runtime_stage_evidence(tmp_path,approved,items,gate)
    assert result[0]['execution_status']=='部分'
    assert result[0]['partial_evidence'][0]['scenario_id']=='AC13-01'
    gate['checks'][0]['observed']=False
    unchanged=[{'requirement_id':'runtime-contract','execution_status':'待实施','evidence_files':[]}]
    assert bind_runtime_stage_evidence(tmp_path,approved,unchanged,gate)==unchanged
def test_deadline_stop_requires_failed_gate_real_timeout_and_unchanged_deadline():
    from project2_continuation_report import classify_runtime_stop
    gate={'stage':'Chap13','repair_rounds':1,'system_gate_executed':True,'gate_scope':'system_gate',
          'failure_items':['same_run_id','unchanged_native_answer_body'],
          'checks':[{'expected':True,'observed':False,'status':'failed'}]}
    saved={'absolute_deadline':100.0,'attempts':5,'llm_calls':1}
    result={'status':'partial','workers':{'database':{'status':'completed'},'rag':{'status':'timeout','error':{'category':'request_deadline_exhausted'}}},
            'usage':{'absolute_deadline':100.0,'attempts':13,'llm_calls':2}}
    decision=classify_runtime_stop(gate,saved,result)
    assert decision['status']=='stopped_frozen_deadline' and not decision['permission_to_increase_budget']
    result['usage']['absolute_deadline']=101.0
    assert classify_runtime_stop(gate,saved,result)['status']=='requires_code_repair'
def test_failed_runtime_gate_can_bind_only_passed_components_as_partial(tmp_path):
    from project2_continuation_report import bind_runtime_stage_evidence
    approved=[{'requirement_id':'runtime-contract','scenario_ids':'AC13-01;AC13-03'}]
    items=[{'requirement_id':'runtime-contract','execution_status':'待实施','evidence_files':[]}]
    gate={'stage':'Chap13','status':'failed','repair_rounds':1,'system_gate_executed':True,'gate_scope':'system_gate',
          'checks':[{'check':'same_run_id','expected':True,'observed':False,'status':'failed'},
                    {'check':'owner_read_resume_isolation','expected':True,'observed':True,'status':'passed'}]}
    folder=tmp_path/'audit/project2-v1/ch13_round1';folder.mkdir(parents=True)
    (folder/'gate.json').write_text(json.dumps(gate),encoding='utf-8')
    result=bind_runtime_stage_evidence(tmp_path,approved,items,gate)
    assert result[0]['execution_status']=='部分'
    assert [x['scenario_id'] for x in result[0]['partial_evidence']]==['AC13-03']
def test_one_page_reports_stop_undefined_kappa_and_every_state_without_claiming_production():
    from project2_v031_report import one_page
    report=json.loads((ROOT/'audit/project2-v1/summary.json').read_text(encoding='utf-8'))
    text=one_page(ROOT,report)
    assert len(text.splitlines())<=55
    assert 'S14未通过' in text and 'κ未定义' in text
    assert '人工抽检' in text and '不称独立人工评分' in text
    assert report['stop_reason'] in text
    assert all(name in text for name in ('completed','partial','no_data','permission_denied','timeout','failed'))
    assert '未执行' in text and '95%CI' in text
