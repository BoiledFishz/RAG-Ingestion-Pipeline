"""Read-only historical diagnosis. Never starts a Worker or reads held-out bodies."""
from __future__ import annotations
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
def lines(name):return [json.loads(x) for x in (ROOT/name).read_text(encoding='utf-8').splitlines()]
def sha(name):return hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
def distribution(values):
    v=sorted(values)
    return {'n':len(v),'min':min(v) if v else None,'median':v[len(v)//2] if v else None,
            'p95':v[math.ceil(.95*len(v))-1] if v else None,'max':max(v) if v else None,
            'mean':sum(v)/len(v) if v else None}
def main():
    folder='audit/project2-v1/ch13_v032_round0/'
    events=read(folder+'resume_trace.json')['events'];cp=read(folder+'before_restart_checkpoint.json')
    accounting=read(folder+'recovery_accounting_evidence.json');startup=read(folder+'after_restart_startup.json')
    resumed=read(folder+'resumed_response.json');rag=resumed['workers']['rag']
    trace_start=next(x['timestamp'] for x in events if x['stage']=='resume')
    db_start=next(x['timestamp'] for x in events if x['stage']=='database' and x['status']=='started')
    db_done=next(x['timestamp'] for x in events if x['stage']=='database' and x['status']=='completed')
    rag_start=next(x['timestamp'] for x in events if x['stage']=='rag' and x['timestamp']>=trace_start)
    end=events[-1]['timestamp'];before=accounting['before'];after=accounting['after']
    llm=[x for x in events if x.get('kind')=='llm' and x['timestamp']>=trace_start]
    qa_path='evals/project2-v1/ch12/regression_repair1/requests.jsonl';qa=lines(qa_path)
    batch_path='evals/project2-v1/calibration_v031/batch2/requests.jsonl';batch=lines(batch_path)
    tune={x['record']['QUESTION_ID']:x['record'] for x in read('evals/protocol_v0/tune.json')}
    failures=[];completed=[]
    for i,row in enumerate(qa):
        w=(row.get('result') or {}).get('workers',{});r=w.get('rag',{});record=tune[row['question_id']]
        q=record['QUESTION_TITLE']+'\n'+record['QUESTION_TEXT']
        preceding=qa[i-1]['result']['workers']['rag'] if i else None
        classification='first service request after startup' if not i else 'after previous RAG timeout: restart inferred from runner/control flow' if preceding and preceding['status']=='timeout' else 'same process not independently recorded'
        meta={'question_id':row['question_id'],'repeat':row['repeat'],'order_in_file':i+1,
            'query_sha256':hashlib.sha256(q.encode()).hexdigest(),'query_characters':len(q),
            'version_mentions':re.findall(r'\b\d+\.\d+(?:\.\d+)*\b',q),
            'platform_mentions':sorted(set(re.findall(r'\b(?:Windows|Linux|UNIX|AIX|Mac|Solaris|RHEL)\b',q,re.I))),
            'question_title':record['QUESTION_TITLE'],'request_seconds':row['elapsed_seconds'],
            'rag_status':r.get('status'),'db_status':w.get('database',{}).get('status'),
            'rag_error':r.get('error'),'usage':row['result']['usage'],
            'startup_classification':classification}
        if r.get('status')=='timeout' and w.get('database',{}).get('status')=='completed':failures.append(meta)
        if r.get('status')=='completed':
            ms=r['payload'].get('trace',{}).get('latency_ms')
            if ms is not None:completed.append({**meta,'rag_seconds':ms/1000})
    assert len(failures)==33,'Historical cohort changed'
    by_repeat={str(i):{'qa_completed_rag_seconds':distribution([x['rag_seconds'] for x in completed if x['repeat']==i]),
                      'qa_rag_timeouts':sum(x['repeat']==i for x in failures),
                      'batch2_rag_only_seconds':distribution([x['elapsed_seconds'] for x in batch if x['path']=='rag_only' and x['repeat']==i])} for i in (1,2,3)}
    batch_protocol=read('evals/project2-v1/calibration_v031/batch2/protocol.json')
    provenance=[folder+x for x in ['resume_trace.json','before_restart_checkpoint.json','recovery_accounting_evidence.json','resumed_response.json','after_restart_startup.json']]+[qa_path,batch_path,'scripts/project2_stage_eval.py','scripts/project2_v03_calibration.py','scripts/run_project2_ch13_gate.py','audit/project2-v1/regression_repair1.log']
    report={'evidence_type':'真实运行（已有记录只读分析；没有新增运行）','budget_seconds':37.941018,
        'chap13':{'node_timings':{'before_restart_database_seconds':db_done-db_start,
            'before_restart_total_saved_active_seconds':before['consumed_seconds'],
            'before_restart_rag':'interrupted; duration right-censored; no completed observation',
            'resume_database_skipped':True,'resume_rag_observed_until_timeout_seconds':end-rag_start,
            'resume_total_active_seconds':after['segments'][-1]['consumed_seconds'],
            'total_active_including_uncertain_tail_and_cleanup':after['consumed_seconds']},
            'cold_start':{'process_launch_to_entry_seconds':startup['process_launch_to_entry_seconds'],
                'launch_to_ready_seconds':startup['parent_launch_to_ready_seconds'],'rag_startup':startup['rag_startup'],
                'counted_in_v032_execution':False,'embedding_inference_warmup_recorded':False},
            'failure_checks':{
                'same_run_id':{'predicate':'HTTP 200 AND original run_id AND overall completed',
                    'http200':True,'id_same':resumed['run_id']==cp['run_id'],'overall':resumed['status'],
                    'failure_reason':'overall partial: DB completed, RAG timeout; ID itself was retained'},
                'unchanged_native_answer_body':{'predicate':'nonempty resumed answer AND its SHA256 appears as NATIVE_BODY in API log',
                    'answer_nonempty':bool(resumed.get('answer')),'failure_reason':'timeout produced empty answer; no completed native body hash to compare'}},
            'trigger':'cumulative execution deadline; 15/19 dependency, 4/6 LLM; not an attempt cap',
            'counterfactual_90_seconds':{'evidence_type':'未执行（推算）','additional_active_seconds':90-37.941018,
                'remaining_after_preserved_segment':90-after['segments'][0]['consumed_seconds'],
                'last_model_call_observed_wait_seconds':end-llm[-1]['timestamp'],
                'model_per_call_timeout_seconds':30,'conclusion':'The observed stop would not occur at 37.941s with 90s. Completion is not guaranteed: last call is censored, later retry/generation path unobserved; native gate must decide.'}},
        'qa':{'requests':len(qa),'rag_timeout_requests':failures,'rag_timeout_total':sum(x['result']['workers']['rag']['status']=='timeout' for x in qa),'cohort_definition':'33 RAG timeout with DB completed; additionally 3 both-Worker timeouts retained separately','completed_rag_seconds':distribution([x['rag_seconds'] for x in completed]),
            'by_repeat':by_repeat,'first_service_request':{'qa':{'rag_seconds':qa[0]['result']['workers']['rag']['payload']['trace']['latency_ms']/1000,'request_seconds':qa[0]['elapsed_seconds']},
                'batch2_rag_only_seconds':next(x['elapsed_seconds'] for x in batch if x['path']=='rag_only')},
            'after_inferred_restart_completed_rag_seconds':distribution([x['rag_seconds'] for x in completed if x['startup_classification'].startswith('after')]),
            'clock_caveat':'RAG trace.latency_ms starts inside agent.run, after index startup. Request elapsed includes DB and on-demand restart; these are not interchangeable. Worker PID and per-request startup timing were not recorded in repair1.',
            'comparison':'Calibration preloads once, executes repeat1/2/3 consecutively per task, uses hot persistent cache and 50 constructed tasks. QA shuffles 39 original questions per repeat; cancellation can force a cold child on subsequent requests. Neither load nor temperature is matched; successful-only QA timings are survivor-biased.',
            'calibration_envelope':batch_protocol['measurement_envelope'],'production_after_calibration_seconds':37.941018},
        'concurrency':{'own_driver':'sequential: one synchronous TestClient request at a time; calibration awaits each run; no overlapping own evaluation requests',
            'same_ollama_other_clients':'unknown: historical service-wide client/process/GPU telemetry absent; cannot infer from current process inventory',
            'interrupted_native_call':'a killed client can leave a pending Ollama request; historical server-side cancellation completion not observed'},
        'heldout_answer_contents_read':False,'source_sha256':{x:sha(x) for x in provenance}}
    path=ROOT/'audit/project2-v1/budget_diagnosis.json'
    if path.exists():raise ValueError('Diagnosis already registered; retain original')
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS read-only diagnosis: QA timeout cohort=33; Chap13 two checks explained; no new requests; held-out bodies not read')
if __name__=='__main__':main()
