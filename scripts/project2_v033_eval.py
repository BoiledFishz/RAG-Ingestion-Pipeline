"""Final bounded tune repair / once-only confirmatory held-out. No LLM scoring."""
from __future__ import annotations
import argparse
import hashlib
import json
import logging
import random
import sys
import time
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from project2_stage_eval import online_question,retrieved_ids,source_lock,select_questions
from project2_v031_calibration import HostGuard,digest,save
from evaluation_protocol.statistics import metric
from project2_v033_metrics import worker_flags
from project2_stage_eval import legacy_capabilities
from evaluation_protocol.runner import document_id,body_f1
from evaluation_protocol.storage import ledger
from run_project2_v03_gate import read_matrix,check_consistency
FOLDER=ROOT/'evals/project2-v1/ch13_v033'
STATES=('completed','partial','no_data','permission_denied','timeout','failed')
def read(p):return json.loads(p.read_text(encoding='utf-8'))

def verify_gate():
    gate=read(ROOT/'audit/project2-v1/v033_chap13_gate.json')
    from summarize_project2 import stage_verdict
    if stage_verdict(gate)!='passed':raise ValueError('Native gate has not passed')

def register():
    verify_gate();FOLDER.mkdir(parents=True,exist_ok=True)
    files=source_lock(ROOT)
    for name in ['enterprise-ai-agent/api/project2_runtime_main.py','specs/project2/v0.3.3/recovery_accounting.json']:
        files[name]=digest(ROOT/name)
    plan={'stage':'Chap13','spec_version':'v0.3.3','gate_repair_round':read(ROOT/'audit/project2-v1/v033_chap13_gate.json')['repair_rounds'],'repeats':3,'seed':20261005,
          'online_files':files,'script_sha256':digest(Path(__file__)),'spec_manifest_sha256':digest(ROOT/'specs/project2/v0.3.3/version_manifest.json'),
          'diagnosis_sha256':digest(ROOT/'audit/project2-v1/regression_diagnosis_round2.json'),
          'scope':'QA原问题39+原登记组合50，各3重复；held-out仅一次确认性运行，不用于设计',
          'query_projection':'official query fields only; gold first enters offline scoring',
          'sampling':'frozen quick + original controls for tune; frozen held-out quick only',
          'smoke_failure_fraction_max':.10,'heldout_global_stage_call_number':2,'llm_scoring':'paused',
          'changes':['signed wall floor 90s','real startup warmup before readiness','Project2 preserves wrapped transport timeout and cancels owned child'],'budget_seconds':90,
          'smoke_numerator':'any Worker failed or timeout, including overall partial',
          'business_samples':50,'qa_tune_questions':39,'business_task_protocol_sha256':digest(ROOT/'evals/project2-v1/calibration_v031/protocol.json'),
          'legacy_capabilities':legacy_capabilities(ROOT),
          'baseline_prompt_and_models':'unchanged frozen v0','no_selective_reruns':True}
    if (FOLDER/'stage.plan.json').exists():
        if read(FOLDER/'stage.plan.json')!=plan:raise ValueError('Registered stage changed')
    else:save(FOLDER/'stage.plan.json',plan)
    return plan

def questions(partition):
    if partition=='tune':return select_questions(ROOT,'tune')
    verify_gate()
    splits=read(ROOT/'splits.json')['partitions'][partition];path=ROOT/splits['file']
    if digest(path)!=splits['sha256']:raise ValueError('Frozen partition changed')
    wanted=set(splits['quick_question_ids'])
    return [x for x in read(path) if x['record']['QUESTION_ID'] in wanted]

def invoke(tasks,output,on_repeat=None):
    sys.path.insert(0,str(ROOT/'enterprise-ai-agent'))
    from api.project2_runtime_main import create_app
    from agents.project2.policy import TrustedContext
    from fastapi.testclient import TestClient
    if output.exists():raise ValueError('Run already started; no selective repeats')
    output.parent.mkdir(parents=True,exist_ok=True)
    owner=TrustedContext('v033-evaluator','local',frozenset({'full'}),frozenset({'document_count','compare_document_counts','rag_explain'}))
    app=create_app(credentials={'v033-local-eval':owner},state_directory=output.parent/'runtime_state')
    matrix=read_matrix(ROOT,'v0.3.1');rows=[]
    with HostGuard(output.parent/'power'),TestClient(app) as client,output.open('x',encoding='utf-8') as handle:
        for repeat in (1,2,3):
            if on_repeat:on_repeat(repeat)
            order=list(tasks);random.Random(20261005+repeat).shuffle(order)
            for index,task in enumerate(order,1):
                ready_started=time.monotonic()
                while not client.get('/healthz').json()['ready']:
                    if time.monotonic()-ready_started>180:raise TimeoutError('Startup readiness did not recover')
                    time.sleep(.1)
                readiness_wait=time.monotonic()-ready_started
                started=time.monotonic();response=None;error=None
                try:
                    reply=client.post('/v2/project2/analysis',headers={'Authorization':'Bearer v033-local-eval'},json=task['body'])
                    response=reply.json();check=check_consistency(response,matrix)
                    if reply.status_code!=200:check['passed']=False
                except Exception as exc:
                    error={'category':type(exc).__name__,'detail':str(exc)[:400]};check={'passed':False}
                row={k:v for k,v in task.items() if k!='body'}
                elapsed=time.monotonic()-started
                row.update(repeat=repeat,result=response,error=error,check=check,elapsed_seconds=elapsed,pre_request_readiness_seconds=readiness_wait,end_to_end_seconds=elapsed+readiness_wait,budget_seconds=90,evidence_type='真实运行')
                handle.write(json.dumps(row,ensure_ascii=False)+'\n');handle.flush();rows.append(row)
                logging.info('v033 %s repeat%d %d/%d %s elapsed=%.3f',output.parent.name,repeat,index,len(order),(response or {}).get('status','failed'),row['elapsed_seconds'])
    save(output.parent/'cleanup_evidence.json',{'observation':app.state.rag_runtime.cleanup_observation,'evidence_type':'真实运行','old_records_rerun':False})
    return rows

def summarize(rows,qs,partition):
    expected={(x['record']['QUESTION_ID'],i,x['group_sha256']) for x in qs for i in (1,2,3)}
    actual=[(x['question_id'],x['repeat'],x['group_sha256']) for x in rows]
    if len(actual)!=len(set(actual)) or set(actual)!=expected:raise ValueError('Incomplete/duplicate frozen slots')
    lookup={x['record']['QUESTION_ID']:x['record'] for x in qs}
    primary=set(read(ROOT/'splits.json')['partitions'][partition]['quick_question_ids'])
    for row in rows:
        record=lookup[row['question_id']];rag=(row['result'] or {}).get('workers',{}).get('rag',{})
        target=record['DOCUMENT'] if record['ANSWERABLE']=='Y' else None;ids=retrieved_ids(rag)
        body=rag.get('payload',{}).get('answer','')
        row.update(worker_flags(row))
        row.update(label=record['ANSWERABLE'],primary=row['question_id'] in primary,
          recall_at_5=int(target in [document_id(x) for x in ids[:5]]) if target else None,
          recall_at_10=int(target in [document_id(x) for x in ids[:10]]) if target else None,
          mrr=next((1/i for i,x in enumerate(ids,1) if document_id(x)==target),0) if target else None,
          body_token_f1=body_f1(body,record['ANSWER']) if target else None,
          n_refusal_proxy=int(rag.get('status')=='no_data') if not target else None,
          complete=int(rag.get('status')=='completed'),partial=int(rag.get('status')=='partial'),
          failed_or_timeout=int((row['result'] or {}).get('status','failed') in {'failed','timeout'}))
    target_dir=FOLDER/('qa-'+partition);save(target_dir/'scored.json',rows)
    # Held-out answer contents are processed only by this fixed scoring/export
    # program, never printed to the designer. Do not change design after this.
    base=read(ROOT/f'evals/protocol_v0/runs/baseline-v0-quick/{partition}/runs.json')
    old={(x['question_id'],x['repeat']):x for x in base};declines=[]
    for row in rows:
        for key in ('recall_at_5','recall_at_10','mrr','body_token_f1','n_refusal_proxy'):
            prior=old.get((row['question_id'],row['repeat']),{}).get(key)
            if prior is not None and row.get(key) is not None and row[key]<prior:
                declines.append({'question_id':row['question_id'],'repeat':row['repeat'],'metric':key,'v0':prior,'current':row[key]})
    chosen=[x for x in rows if x['primary']]
    counts=Counter((x['result'] or {}).get('status','failed') for x in rows)
    if set(counts)-set(STATES):raise ValueError('Unknown state')
    distributions={state:counts[state] for state in STATES};assert sum(distributions.values())==len(rows)
    smoke=metric(rows,'any_worker_failed_or_timeout',binary=True)
    controls={x['question_id'] for x in read(ROOT/'evals/protocol_v0/controls.json')['records']} if partition=='tune' else set()
    summary={'partition':partition,'requests':len(rows),'repeats':3,
        'scope':'仅 tune/对照集，非 held-out 验证' if partition=='tune' else '修复后第一次确认性运行；累计第2次阶段调用/3次重复',
        'state_distribution':distributions,'budget_seconds':90,'smoke':smoke,
        'end_to_end_latency':metric(rows,'end_to_end_seconds'),
        'worker_failures':{k:metric(rows,k,binary=True) for k in ('any_worker_failed_or_timeout','rag_failed_or_timeout','database_failed_or_timeout')},
        'worker_failure_items':[{'question_id':x['question_id'],'repeat':x['repeat'],'workers':{k:{'status':v['status'],'error':v.get('error')} for k,v in (x.get('result') or {}).get('workers',{}).items()}} for x in rows if x['any_worker_failed_or_timeout']],
        'smoke_passed':smoke['numerator']/smoke['denominator']<=.10,
        'metrics':{k:metric(chosen,k,binary=k not in {'mrr','body_token_f1','elapsed_seconds'}) for k in ('recall_at_5','recall_at_10','mrr','body_token_f1','n_refusal_proxy','complete','partial','elapsed_seconds')},
        'regression_items':declines,'control_regressed_questions':len({x['question_id'] for x in declines if x['question_id'] in controls}),
        'control_regressed_question_repeats':len({(x['question_id'],x['repeat']) for x in declines if x['question_id'] in controls}),
        'required_facts':{'status':'待盲评','LLM_scoring':'paused','empty_or_failed_auto_zero_observations':sum(not x['result'] or x['result'].get('workers',{}).get('rag',{}).get('status') in {'failed','timeout'} or not x['result'].get('answer','').strip() for x in rows)},
        'source_sha256':digest(target_dir/'requests.jsonl'),'plan_sha256':digest(FOLDER/'stage.plan.json'),
        'baseline_metrics':{k:metric([x for x in base if x.get('primary',True) and x['question_id'] in primary],k,binary=k!='mrr') for k in ('recall_at_5','recall_at_10','mrr')},
        's14_status':'未通过','quality_acceptance_claim':False}
    save(target_dir/'summary.json',summary);return summary

def run(partition):
    if partition=='business':return business_run()
    plan=register()
    for name,value in plan['online_files'].items():
        if digest(ROOT/name)!=value:raise ValueError('Source changed after code freeze: '+name)
    receipt=FOLDER/'heldout_receipt.json'
    if partition=='held-out':
        if receipt.exists():raise ValueError('Confirmatory invocation already consumed')
        tune=read(FOLDER/'qa-tune/summary.json')
        business=read(FOLDER/'business/summary.json')
        if not tune['smoke_passed'] or not business['smoke_passed']:raise ValueError('Worker smoke exceeds 10% on tune QA or combined tasks; held-out must not run')
        old=read(ROOT/'evals/project2-v1/ch12/heldout_receipt.json')
        assert old['heldout_stage_calls_project2']==1 and old['heldout_repetitions_project2']==3
        event=ledger('stage_started','project2-ch13-v033',config='project2-v033',scope='quick',planned_repeats=3,stage_plan_sha256=digest(FOLDER/'stage.plan.json'))
        save(receipt,{'stage':'Chap13','status':'started','new_stage_calls':1,'new_repetitions':0,
              'global_stage_calls':2,'global_repetitions':3,'ledger_entry_sha256':event['entry_sha256'],'previous_receipt_sha256':digest(ROOT/'evals/project2-v1/ch12/heldout_receipt.json')})
    qs=questions(partition)
    tasks=[{'question_id':x['record']['QUESTION_ID'],'group_sha256':x['group_sha256'],'body':online_question(x['record'])} for x in qs]
    def repeat_started(repeat):
        value=read(receipt);assert value['new_repetitions']+1==repeat
        value['new_repetitions']=repeat;value['global_repetitions']=3+repeat;save(receipt,value)
        ledger('repeat_started','project2-ch13-v033',repeat=repeat)
    rows=invoke(tasks,FOLDER/('qa-'+partition)/'requests.jsonl',repeat_started if partition=='held-out' else None)
    summary=summarize(rows,qs,partition)
    if partition=='held-out':
        value=read(receipt);value.update(status='completed',requests=len(rows),summary_sha256=digest(FOLDER/'qa-held-out/summary.json'));save(receipt,value)
        ledger('stage_finished','project2-ch13-v033',status='completed',summary_sha256=value['summary_sha256'])
    logging.info('%s final states=%s; tune smoke=%s',partition,summary['state_distribution'],summary['smoke_passed'])
    return summary

def business_run():
    plan=register()
    protocol=read(ROOT/'evals/project2-v1/calibration_v031/protocol.json')
    tasks=[{'sample_id':s['sample_id'],'group_sha256':s['query_sha256'],
        'body':{k:v for k,v in s.items() if k not in {'sample_id','query_sha256'}}} for s in protocol['samples']]
    rows=invoke(tasks,FOLDER/'business/requests.jsonl')
    reference=read(ROOT/'audit/project2-v1/preflight_report.json')['sample_measurements']
    for row in rows:
        data=row.get('result') or {};groups=data.get('workers',{}).get('database',{}).get('payload',{}).get('groups',[])
        row.update(worker_flags(row));row['count_exact']=int([x['count'] for x in groups]==reference[row['sample_id']]['counts'])
        row['complete']=int(data.get('status')=='completed');row['trace_conformance']=int(row['check']['passed'])
        row['llm_calls']=data.get('usage',{}).get('llm_calls');row['attempts']=data.get('usage',{}).get('attempts')
    counts=Counter((x.get('result') or {}).get('status','failed') for x in rows)
    states={s:counts[s] for s in STATES};assert sum(states.values())==len(rows)==150
    smoke=metric(rows,'any_worker_failed_or_timeout',binary=True)
    summary={'requests':len(rows),'repeats':3,'budget_seconds':90,'state_distribution':states,
        'end_to_end_latency':metric(rows,'end_to_end_seconds'),
        'smoke':smoke,'smoke_passed':smoke['numerator']/smoke['denominator']<=.10,
        'metrics':{k:metric(rows,k,binary=k in {'complete','count_exact','trace_conformance'}) for k in ('complete','count_exact','trace_conformance','attempts','llm_calls','elapsed_seconds')},
        'worker_failures':{k:metric(rows,k,binary=True) for k in ('any_worker_failed_or_timeout','rag_failed_or_timeout','database_failed_or_timeout')},
        'worker_failure_items':[{'sample_id':x['sample_id'],'repeat':x['repeat'],'workers':{k:{'status':v['status'],'error':v.get('error')} for k,v in (x.get('result') or {}).get('workers',{}).items()}} for x in rows if x['any_worker_failed_or_timeout']],
        'regression_items':[{'sample_id':x['sample_id'],'repeat':x['repeat'],'status':(x.get('result') or {}).get('status'),'counts_exact':bool(x['count_exact'])} for x in rows if not x['complete'] or not x['count_exact']],
        'legacy':{k:{**v,'unsupported_numerator':len(rows),'task_denominator':len(rows)} for k,v in plan['legacy_capabilities'].items()},
        'superiority_claim':False,'required_facts':'only frozen QA has human-approved definitions; unannotated business tasks unscored',
        'scope':'仅 tune/对照集，非 held-out 验证','source_sha256':digest(FOLDER/'business/requests.jsonl')}
    save(FOLDER/'business/scored.json',rows);save(FOLDER/'business/summary.json',summary)
    logging.info('v033 business states=%s worker smoke passed=%s',states,summary['smoke_passed'])
    return summary

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--partition',choices=['tune','business','held-out'],required=True);args=ap.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    summary=run(args.partition)
    raise SystemExit(0 if args.partition=='held-out' or summary['smoke_passed'] else 1)
