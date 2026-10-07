"""Offline, tune-only attribution before the final bounded repair; no model calls."""
from __future__ import annotations
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from project2_stage_eval import select_questions,online_question

def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def save(p,d):
    path=ROOT/p;path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise ValueError('Evidence already registered; do not overwrite')
    path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    gate=read('audit/project2-v1/ch13_round1/gate.json')
    checkpoint=read('audit/project2-v1/ch13_round1/before_restart_checkpoint.json')
    resumed=read('audit/project2-v1/ch13_round1/resumed_response.json')
    failures=[x['check'] for x in gate['checks'] if x['status']=='failed']
    assert set(failures)=={'same_run_id','unchanged_native_answer_body'}
    save('audit/project2-v1/v032_previous_gate_failures.json',{
        'checks':[{'name':'same_run_id','reason':'ID was preserved, but composite predicate also required completed; actual partial (DB completed, RAG timeout)',
                   'same_id_observed':resumed['run_id']==checkpoint['run_id']},
                  {'name':'unchanged_native_answer_body','reason':'Timeout yielded no nonempty native body; therefore unchanged-body hash proof was absent',
                   'nonempty_body_observed':bool(resumed.get('answer'))}],
        'trigger':'request_deadline_exhausted; old absolute deadline included stopped/index-loading time',
        'usage':resumed['usage'],'numeric_limits_changed':False,
        'source_files':{p:sha(p) for p in ['audit/project2-v1/ch13_round1/gate.json','audit/project2-v1/ch13_round1/before_restart_checkpoint.json','audit/project2-v1/ch13_round1/resumed_response.json']}})
    folder='evals/project2-v1/ch12/regression_repair1/'
    rows=read(folder+'scored.json');summary=read(folder+'summary.json')
    baseline={(x['question_id'],x['repeat']):x for x in read('evals/protocol_v0/runs/baseline-v0-quick/tune/runs.json')}
    controls={x['question_id'] for x in read('evals/protocol_v0/controls.json')['records']}
    pairs={(x['question_id'],x['repeat']) for x in summary['regression_items'] if x['question_id'] in controls}
    questions={x['record']['QUESTION_ID']:online_question(x['record'])['query'] for x in select_questions(ROOT,'tune')}
    items=[]
    for qid in sorted({x[0] for x in pairs}):
        observations=[]
        for row in rows:
            if row['question_id']!=qid:continue
            result=row['result'];rag=result['workers']['rag'];old=baseline[(qid,row['repeat'])]
            payload=rag.get('payload',{});regressed=(qid,row['repeat']) in pairs
            category='no_decline';own_bug=False
            if regressed:
                if rag['status']=='timeout':category='预算/超时导致的partial或timeout'
                elif payload.get('pipeline',{}).get('candidate_ids')!=old['native'].get('pipeline',{}).get('candidate_ids'):
                    category='检索结果变化';reason='frozen v0 query-rewrite/model variance; no P2 ranking algorithm change'
                elif payload.get('trace',{}).get('evidence')!=old['native']['run'].get('trace',{}).get('evidence'):
                    category='证据映射或上下文压缩变化'
                else:category='回答生成变化'
            observations.append({'repeat':row['repeat'],'regressed':regressed,'category':category,'status':result['status'],
                'worker_statuses':{k:v['status'] for k,v in result['workers'].items()},'error':rag.get('error'),
                'usage':result['usage'],'trace':payload.get('trace'),'pipeline':payload.get('pipeline'),
                'v0_trace':old['native']['run'].get('trace'),'v0_pipeline':old['native'].get('pipeline'),
                'metric_comparison':{k:{'v0':old[k],'current':row[k]} for k in ('recall_at_5','recall_at_10','mrr','body_token_f1')},
                'scoring_missing':any(x['question_id']==qid and x['repeat']==row['repeat'] for x in summary['required_facts']['unscored']),
                'evidence_file':folder+'scored.json','repair_eligible':own_bug})
        categories=Counter(x['category'] for x in observations if x['regressed'])
        items.append({'question_id':qid,'primary_category':categories.most_common(1)[0][0],
                      'observations':observations,'decision':'Frozen budget/v0 behavior; no answer or ranking repair'})
    def classify(row):
        result=row['result'];workers=result['workers'];status=result['status']
        errors={k:v.get('error') for k,v in workers.items()}
        category=('P2_slot_parser_missing_literal_component' if status=='failed' and all((v or {}).get('category')=='clarification_required' for v in errors.values())
                  else 'frozen_database_statement_limit' if workers['database']['status']=='timeout'
                  else 'frozen_request_deadline_or_cold_restart' if workers['rag']['status']=='timeout'
                  else 'v0_RAG_refusal_with_real_DB_data' if workers['rag']['status']=='no_data'
                  else 'DB_no_data_only_not_quality_regression' if workers['database']['status']=='no_data' else 'other')
        return {'question_id':row.get('question_id'),'sample_id':row.get('sample_id'),'repeat':row['repeat'],
            'status':status,'worker_statuses':{k:v['status'] for k,v in workers.items()},'errors':errors,
            'category':category,'query':questions.get(row.get('question_id')),'usage':result['usage'],
            'evidence':'原始JSONL/scored记录；不补测'}
    cases=[classify(x) for x in rows if x['result']['status'] in {'failed','timeout','partial'}]
    business=[json.loads(x) for x in (ROOT/'evals/project2-v1/ch12/business.requests.jsonl').read_text(encoding='utf-8').splitlines()]
    business_failed=[classify(x) for x in business if x['result']['status']=='failed']
    counts=Counter(x['status'] for x in cases)
    assert (len(items),counts['failed'],counts['timeout'],counts['partial'],len(business_failed))==(9,6,3,41,6)
    save('audit/project2-v1/regression_diagnosis_round2.json',{'scope':'仅 tune/对照集，非 held-out 验证','repair_round':2,
        'heldout_bodies_read':False,'control_regressed_questions':len(items),'items':items,
        'primary_attribution_distribution':dict(Counter(x['primary_category'] for x in items)),
        'qa_cases':cases,'qa_category_distribution':dict(Counter(x['category'] for x in cases)),
        'business_failed_cases':business_failed,'business_category_distribution':dict(Counter(x['category'] for x in business_failed)),
        'partial_DB_no_data_only':sum(x['category']=='DB_no_data_only_not_quality_regression' for x in cases),
        'repair_candidates':['query-side literal Portal product missing from known-component matcher','owned process shutdown access denied'],
        'sources':{p:sha(p) for p in [folder+'scored.json',folder+'summary.json','evals/project2-v1/ch12/business.requests.jsonl']}})
    score='evals/project2-v1/ch12/second_scoring'
    save(score+'/invalidation.json',{'status':'作废：空正文、全同分、基于修复前答案','authorization_date':'2026-10-06',
        'llm_scoring':'paused','agreement_eligible':False,'independent_human_scoring':False,
        'files':{p.relative_to(ROOT).as_posix():sha(p.relative_to(ROOT)) for p in sorted((ROOT/score).glob('*')) if p.is_file()},
        'original_records_preserved':True,'replacement':'待盲评；禁止3B模型评分'})
    print(json.dumps({'previous_failed_checks':failures,'remaining_controls':len(items),'qa_categories':dict(Counter(x['category'] for x in cases)),
         'business_failed':len(business_failed),'scoring':'作废；待盲评'},ensure_ascii=False))

if __name__=='__main__':main()
