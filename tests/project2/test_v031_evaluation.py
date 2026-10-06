"""Evaluation boundary tests; fixtures are original TechQA questions."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/'scripts/project2_stage_eval.py'

def load():
    spec=importlib.util.spec_from_file_location('p2_stage_eval',SCRIPT)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def test_original_query_projection_has_no_gold_or_identity():
    module=load()
    row=json.loads((ROOT/'evals/protocol_v0/tune.json').read_text(encoding='utf-8'))[0]['record']
    body=module.online_question(row)
    assert set(body)=={'query','analysis_operation','include_samples','sample_limit'}
    row={**row,'ANSWER':'this field may never influence input','DOC_IDS':['sentinel'],'ANSWERABLE':'N','QUESTION_ID':'sentinel'}
    assert body==module.online_question(row)

def test_heldout_is_not_opened_before_full_gate(tmp_path):
    module=load()
    (tmp_path/'evals/protocol_v0').mkdir(parents=True)
    (tmp_path/'evals/protocol_v0/held-out.json').write_text('not valid JSON')
    with pytest.raises(ValueError,match='full engineering gate'):
        module.select_questions(tmp_path,'held-out')

def test_old_capability_check_requires_real_schema_or_tools():
    module=load()
    caps=module.legacy_capabilities(ROOT)
    assert set(caps)=={'single_agent','fixed_workflow'}
    assert all(x['status']=='unsupported' for x in caps.values())
    assert all(x['source_sha256'] and x['missing_capability']=='independent_full_corpus_count' for x in caps.values())

def test_ci_preserves_three_repeats_and_independent_denominator():
    module=load()
    rows=[{'repeat':repeat,'group_sha256':str(i),'metric':int(i<3)} for repeat in (1,2,3) for i in range(5)]
    value=module.measure_metric(rows,'metric',binary=True)
    assert value['numerator']==9 and value['denominator']==15
    assert len(value['per_repeat'])==3 and value['independent_query_groups']==5
    assert value['interpretation']=='仅描述，不作结论' and value['ci95']

def test_fact_rating_reuse_requires_exact_answer_and_fact_hashes():
    module=load()
    file=ROOT/'evals/protocol_v0/runs/baseline-v0-quick/tune/human_ratings.json'
    original=json.loads(file.read_text(encoding='utf-8'))['items'][0]
    row={'question_id':original['question_id'],'label':'Y','repeat':1,'group_sha256':'original-query',
         'primary':True,'result':{'workers':{'rag':{'payload':{'answer':original['answer_body']}}}}}
    reused=module.reuse_fact_ratings(ROOT,'tune',[row])
    assert reused['matched_answer_observations']==1 and reused['unscored_answer_observations']==0
    row['result']['workers']['rag']['payload']['answer']+='\nChanged answer: needs independent review.'
    pending=module.reuse_fact_ratings(ROOT,'tune',[row])
    assert pending['matched_answer_observations']==0 and pending['unscored_answer_observations']==1

def test_heldout_repeat_counter_counts_starts_not_plans(tmp_path):
    module=load();path=tmp_path/'receipt.json'
    path.write_text(json.dumps({'planned_repeats':3,'heldout_repetitions_project2':0}))
    module.record_repeat(path,1)
    assert json.loads(path.read_text())['heldout_repetitions_project2']==1
    with pytest.raises(ValueError):module.record_repeat(path,1)
    with pytest.raises(ValueError):module.record_repeat(path,3)

def test_failed_inference_cannot_disappear_from_recall_denominator():
    module=load()
    assert module.retrieved_ids({'status':'failed','payload':{}})==[]
    with pytest.raises(ValueError,match='pipeline stage'):
        module.retrieved_ids({'status':'completed','payload':{'trace':{'candidate_ids':['parent stage is not comparable']}}})
