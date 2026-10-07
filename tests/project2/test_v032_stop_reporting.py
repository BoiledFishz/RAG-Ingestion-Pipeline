import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))

def test_current_active_time_failure_is_not_an_absolute_restart_deadline():
    from project2_v032_report import classify_stop
    folder=ROOT/'audit/project2-v1/ch13_v032_round0'
    read=lambda name:json.loads((folder/name).read_text(encoding='utf-8'))
    result=classify_stop(read('gate.json'),read('resumed_response.json'),read('recovery_accounting_evidence.json'))
    assert result['status']=='stopped_frozen_active_execution'
    assert result['machine_predicate'] and result['permission_to_increase_budget'] is False
    assert result['stochastic_rerun_permitted'] is False

def test_stop_requires_actual_timeout_not_just_a_prose_claim():
    from project2_v032_report import classify_stop
    folder=ROOT/'audit/project2-v1/ch13_v032_round0'
    read=lambda name:json.loads((folder/name).read_text(encoding='utf-8'))
    response=read('resumed_response.json');response['workers']['rag']['status']='completed'
    assert not classify_stop(read('gate.json'),response,read('recovery_accounting_evidence.json'))['machine_predicate']

def test_current_report_discloses_failure_and_never_cites_invalid_agreement():
    read=lambda name:json.loads((ROOT/name).read_text(encoding='utf-8'))
    report=read('audit/project2-v1/summary.json')
    page=(ROOT/'specs/project2/summary.md').read_text(encoding='utf-8')
    assert report['s14_status']=='未通过' and report['stages'][1]['status']=='failed'
    assert report['chap13_heldout_new_calls']==0 and report['heldout_stage_calls_project2']==1
    assert report['scoring_status']=='待盲评' and report['agreement_quoted'] is False
    assert 'κ' not in page and '103/103' not in page
    assert len(page.splitlines())<=55
    for distribution in report['state_distributions'].values():
        assert set(distribution['counts'])=={'completed','partial','no_data','permission_denied','timeout','failed'}
        assert sum(distribution['counts'].values())==distribution['denominator']
    assert sum(report['traceability_counts'].values())==report['two_table_consistency']['approved_rows']

def test_blind_pack_nonempty_and_has_no_identity_or_old_score():
    read=lambda path:json.loads((ROOT/path).read_text(encoding='utf-8'))
    receipt=read('audit/project2-v1/v032_blind_export_receipt.json')
    pack=read(receipt['public_json']);key=read(receipt['key_file'])
    forbidden={'system','partition','version','question_id','old_score','label','source_file'}
    assert all(not forbidden & item.keys() for item in pack['items'])
    assert all(item['answer_body'].strip() for item in pack['items'])
    assert all(rating['score'] is None for item in pack['items'] for rating in item['ratings'])
    assert {x['blind_id'] for x in pack['items']}=={x['blind_id'] for x in key['keys']}
    assert receipt['nonempty_answer_observations']+receipt['auto_zero_observations']==receipt['all_observations']
    assert all(x['assigned_fact_score']==0 and x['agreement_eligible'] is False for x in key['automatic_zero'])
    assert receipt['current_v032_acceptance'] is False and receipt['LLM_calls']==0
