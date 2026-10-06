"""Stage-end Project 2 comparisons and frozen QA evaluation, never a gate substitute."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import logging
import random
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from evaluation_protocol.statistics import metric as measure_metric
from evaluation_protocol.storage import query
from project2_v031_calibration import HostGuard, digest, save
from run_project2_v03_gate import read_matrix, check_consistency

LOGGER=logging.getLogger(__name__)
STAGES={'ch12','ch13','ch14','ch15'}

def online_question(record: dict) -> dict:
    # Deliberately read only the two official query fields.
    return {'query':query(record),'analysis_operation':'document_count','include_samples':True,'sample_limit':5}

def retrieved_ids(rag: dict) -> list[str]:
    payload=rag.get('payload',{});pipeline=payload.get('pipeline',{})
    if 'candidate_ids' in pipeline:return pipeline['candidate_ids']
    if rag.get('status') in {'completed','partial'}:
        raise ValueError('Comparable retrieval pipeline stage was not recorded')
    # End-to-end failure returns no retrieved contexts, rather than leaving the denominator.
    return []

def require_gate(root: Path, stage: str) -> dict:
    path=root/f'audit/project2-v1/v031_chap{stage[2:]}_gate.json'
    gate=json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None
    if not gate or gate.get('status')!='passed' or not gate.get('system_gate_executed'):
        raise ValueError('Stage full engineering gate has not passed')
    return gate

def select_questions(root: Path, partition: str, stage: str='ch12') -> list[dict]:
    if partition=='held-out':require_gate(root,stage)
    manifest=json.loads((root/'splits.json').read_text(encoding='utf-8'))
    metadata=manifest['partitions'][partition];path=root/metadata['file']
    if digest(path)!=metadata['sha256']:raise ValueError('Frozen partition hash changed')
    rows=json.loads(path.read_text(encoding='utf-8'))
    wanted=set(metadata['quick_question_ids'])
    if partition=='tune':
        controls=json.loads((root/'evals/protocol_v0/controls.json').read_text(encoding='utf-8'))
        wanted.update(x['question_id'] for x in controls['records'])
    return [x for x in rows if x['record']['QUESTION_ID'] in wanted]

def legacy_capabilities(root: Path) -> dict:
    single=root/'agentic-rag-homework/agents/systems.py'
    parsed=ast.parse(single.read_text(encoding='utf-8'))
    cls=next(x for x in parsed.body if isinstance(x,ast.ClassDef) and x.name=='SingleAgentVersion')
    attrs={x.attr for x in ast.walk(cls) if isinstance(x,ast.Attribute)}
    if attrs!={'research','run','response','metrics'}:raise ValueError('Single Agent contract changed; capability must be rechecked')
    fixed=root/'enterprise-ai-agent/models/schemas.py'
    parsed=ast.parse(fixed.read_text(encoding='utf-8'))
    cls=next(x for x in parsed.body if isinstance(x,ast.ClassDef) and x.name=='QueryRequest')
    fields={x.target.id for x in cls.body if isinstance(x,ast.AnnAssign) and isinstance(x.target,ast.Name)}
    if fields!={'query','filters'}:raise ValueError('Fixed Workflow request capability changed')
    return {name:{'status':'unsupported','missing_capability':'independent_full_corpus_count',
                  'source':path.relative_to(root).as_posix(),'source_sha256':digest(path),
                  'evidence_type':'未执行','evidence_basis':'original source contract; combined task not invoked',
                  'actual_model_calls':0,'cost_comparison_eligible':False}
            for name,path in [('single_agent',single),('fixed_workflow',fixed)]}

def source_lock(root: Path) -> dict:
    files=[]
    for path in (root/'enterprise-ai-agent').rglob('*.py'):
        if 'project2' in path.parts or path.name=='project2_main.py' or path.name=='techqa_document_query.py':files.append(path)
    baseline=json.loads((root/'evals/protocol_v0/baseline_v0.config.json').read_text(encoding='utf-8'))
    files.extend(root/name for name in baseline['sut']['files'])
    files.append(root/'evals/project2-v1/calibration_v031/budget_frozen.json')
    return {x.relative_to(root).as_posix():digest(x) for x in sorted(set(files))}

def register(root: Path, stage: str) -> dict:
    folder=root/f'evals/project2-v1/{stage}';path=folder/'stage.plan.json'
    protocol=root/'evals/project2-v1/calibration_v031/protocol.json'
    value={'stage':stage,'spec_version':'v0.3.1','repeats':3,'seed':20261005,
           'task_protocol_sha256':digest(protocol),'online_files':source_lock(root),
           'legacy_capabilities':legacy_capabilities(root),'qa_scope':'frozen quick + tune controls',
           'heldout_rule':'one invocation per stage, three repeats; errors retained; no re-selection',
           'fact_scoring':'body only; two independent raters required; missing new ratings explicitly pending',
           'acceptance':'architecture coverage comparison; unsupported excluded from answer-quality and cost comparison',
           'gold_fields_online':False}
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8'))!=value:raise ValueError('Stage configuration already locked')
    else:save(path,value);(folder/'stage.plan.json.sha256').write_text(digest(path)+'\n',encoding='utf-8')
    return value

def verify_plan(root: Path, stage: str) -> dict:
    path=root/f'evals/project2-v1/{stage}/stage.plan.json'
    plan=json.loads(path.read_text(encoding='utf-8'))
    if digest(path)!=path.with_suffix('.json.sha256').read_text().strip():raise ValueError('Stage plan changed')
    for name,sha in plan['online_files'].items():
        if digest(root/name)!=sha:raise ValueError('Online configuration changed after lock: '+name)
    return plan

def record_repeat(receipt: Path, repeat: int) -> None:
    data=json.loads(receipt.read_text(encoding='utf-8'))
    if repeat!=data['heldout_repetitions_project2']+1 or repeat>data['planned_repeats']:
        raise ValueError('Duplicate or out-of-order held-out repeat start')
    data['heldout_repetitions_project2']=repeat;save(receipt,data)

def invoke(root: Path, tasks: list[dict], output: Path, stage: str, on_repeat=None) -> list[dict]:
    sys.path.insert(0,str(root/'enterprise-ai-agent'))
    from api.project2_main import create_app
    from agents.project2.policy import TrustedContext
    from fastapi.testclient import TestClient
    if output.exists():raise ValueError('Requests already exist; no selective rerun')
    output.parent.mkdir(parents=True,exist_ok=True)
    owner=TrustedContext('stage-evaluator','local',frozenset({'full'}),frozenset({'document_count','compare_document_counts','rag_explain'}))
    matrix=read_matrix(root,'v0.3.1');rows=[]
    app=create_app(credentials={'local-stage-evaluation':owner})
    with HostGuard(output.parent/'power'), TestClient(app) as client, output.open('x',encoding='utf-8') as handle:
        for repeat in (1,2,3):
            if on_repeat is not None:on_repeat(repeat)
            order=list(tasks);random.Random(20261005+repeat).shuffle(order)
            for index,task in enumerate(order,1):
                started=time.monotonic();response=None;error=None
                try:
                    request=client.post('/v1/project2/analysis',headers={'Authorization':'Bearer local-stage-evaluation'},json=task['body'])
                    response=request.json();check=check_consistency(response,matrix)
                    if request.status_code!=200:check['passed']=False
                except Exception as exc:
                    error={'category':type(exc).__name__,'detail':str(exc)[:400]};check={'passed':False}
                row={k:v for k,v in task.items() if k!='body'}
                row.update({'repeat':repeat,'result':response,'error':error,'check':check,
                            'elapsed_seconds':time.monotonic()-started,'evidence_type':'真实运行'})
                handle.write(json.dumps(row,ensure_ascii=False)+'\n');handle.flush();rows.append(row)
                LOGGER.info('%s repeat%d %d/%d elapsed=%.3f',stage,repeat,index,len(order),row['elapsed_seconds'])
    return rows

def business(root: Path, stage: str) -> dict:
    require_gate(root,stage);plan=verify_plan(root,stage)
    folder=root/f'evals/project2-v1/{stage}'
    protocol=json.loads((root/'evals/project2-v1/calibration_v031/protocol.json').read_text(encoding='utf-8'))
    tasks=[{'sample_id':s['sample_id'],'group_sha256':s['query_sha256'],
            'body':{k:v for k,v in s.items() if k not in {'sample_id','query_sha256'}}} for s in protocol['samples']]
    rows=invoke(root,tasks,folder/'business.requests.jsonl',stage)
    # Independent full-corpus reference was registered before any Worker measurements.
    reference=json.loads((root/'audit/project2-v1/preflight_report.json').read_text(encoding='utf-8'))['sample_measurements']
    declines=[]
    for row in rows:
        data=row.get('result') or {};groups=(data.get('workers',{}).get('database',{}).get('payload') or {}).get('groups',[])
        row['complete']=int(data.get('status')=='completed');row['partial']=int(data.get('status')=='partial')
        row['trace_conformance']=int(row['check']['passed'])
        row['count_exact']=int([x['count'] for x in groups]==reference[row['sample_id']]['counts'])
        row['attempts']=(data.get('usage') or {}).get('attempts');row['llm_calls']=(data.get('usage') or {}).get('llm_calls')
        if not row['complete'] or not row['count_exact']:declines.append({'sample_id':row['sample_id'],'repeat':row['repeat'],'status':data.get('status'),'counts_exact':bool(row['count_exact'])})
    metrics={name:measure_metric(rows,name,binary=name in {'complete','partial','count_exact','trace_conformance'}) for name in ('complete','partial','count_exact','trace_conformance','attempts','llm_calls','elapsed_seconds')}
    unsupported=[{**task,'repeat':repeat,'status':'unsupported','system':name,'missing_capability':cap['missing_capability'],
                  'actual_invocations':0,'evidence_type':'未执行'} for name,cap in plan['legacy_capabilities'].items() for repeat in (1,2,3) for task in [{k:v for k,v in x.items() if k!='body'} for x in tasks]]
    save(folder/'legacy.unsupported.json',unsupported)
    value={'stage':stage,'repeats':3,'independent_tasks':len(tasks),'requests':len(rows),'new_version':metrics,
           'legacy':{name:{**cap,'unsupported_numerator':len(tasks)*3,'task_denominator':len(tasks)*3} for name,cap in plan['legacy_capabilities'].items()},
           'regression_items':declines,'quality_comparison':'not comparable: original combined-task capability unsupported',
           'superiority_claim':False,'required_facts':'separate frozen QA score; unannotated business tasks unscored',
           'request_sha256':digest(folder/'business.requests.jsonl'),'stage_plan_sha256':digest(folder/'stage.plan.json')}
    save(folder/'summary.json',value);return value

def reuse_fact_ratings(root: Path, partition: str, rows: list[dict]) -> dict:
    from evaluation_protocol.annotations import fact_signature
    state=root/'evals/protocol_v0'
    def frozen(path):
        if digest(path)!=path.with_suffix(path.suffix+'.sha256').read_text().split()[0]:raise ValueError('Annotation hash changed: '+str(path))
        return json.loads(path.read_text(encoding='utf-8'))
    definitions={x['question_id']:x for x in frozen(state/f'facts_{partition}.human_frozen.json')['items']}
    indexes={'human':{},'llm':{}};provenance=[]
    # Retrospective reuse never assigns a score to a changed answer or definition.
    for directory in sorted((state/'runs').glob('*/'+partition)):
        for role in indexes:
            path=directory/f'{role}_ratings.json'
            if not path.is_file() or not path.with_suffix('.json.sha256').is_file():continue
            payload=frozen(path)
            if not payload.get('independent') or not payload.get('annotator') or bool(payload.get('is_human'))!=(role=='human'):continue
            for item in payload['items']:
                definition=definitions.get(item['question_id'])
                if not definition or not definition.get('human_approved'):continue
                if item['facts_sha256']!=fact_signature(definition['required_facts']):continue
                if hashlib.sha256(item['answer_body'].encode()).hexdigest()!=item['answer_sha256']:raise ValueError('Rating answer hash mismatch')
                key=(item['question_id'],item['answer_sha256'])
                if key in indexes[role]:
                    previous=indexes[role][key]['item']
                    if [x['score'] for x in previous['facts']]!=[x['score'] for x in item['facts']]:raise ValueError('Conflicting independent ratings for identical answer; adjudication needed')
                indexes[role][key]={'item':item,'annotator':payload['annotator'],'path':path.relative_to(root).as_posix(),'sha256':digest(path)}
            provenance.append({'role':role,'path':path.relative_to(root).as_posix(),'sha256':digest(path)})
    scored=[];unscored=[];exceptions=[];disagreements=[];agreement=[]
    for row in rows:
        if row['label']!='Y':continue
        body=(row.get('result') or {}).get('workers',{}).get('rag',{}).get('payload',{}).get('answer','')
        key=(row['question_id'],hashlib.sha256(body.encode()).hexdigest())
        pair={role:index.get(key) for role,index in indexes.items()}
        if not all(pair.values()) or pair['human']['annotator']==pair['llm']['annotator']:
            unscored.append({'question_id':row['question_id'],'repeat':row['repeat'],'answer_sha256':key[1],'status':'pending_independent_ratings'});continue
        result={name:row[name] for name in ('question_id','repeat','group_sha256','primary')}
        for role,value in pair.items():
            facts=value['item']['facts'];points=sum(x['score'] for x in facts)
            result[role+'_coverage']=points/(2*len(facts));result[role+'_points']=points;result[role+'_possible']=2*len(facts)
        definition=definitions[row['question_id']]
        if len(definition['required_facts'])==1:
            exceptions.append(result);continue
        scored.append(result)
        for a,b in zip(pair['human']['item']['facts'],pair['llm']['item']['facts'],strict=True):
            agreement.append({**result,'agreement':int(a['score']==b['score'])})
            if a['score']!=b['score']:disagreements.append({'question_id':row['question_id'],'answer_sha256':key[1],'fact_id':a['fact_id'],'human_score':a['score'],'llm_score':b['score'],'status':'unresolved'})
    metrics={role:measure_metric([x for x in scored if x['primary']],role+'_coverage') for role in indexes}
    for role,value in metrics.items():
        chosen=[x for x in scored if x['primary']]
        value.update({'earned_points':sum(x[role+'_points'] for x in chosen),'possible_points':sum(x[role+'_possible'] for x in chosen),
                      'aggregation':'macro question coverage; single-fact exceptions excluded'})
    return {'status':'complete_exact_hash_reuse' if not unscored else 'partial_exact_hash_reuse',
            'matched_answer_observations':len(scored)+len(exceptions),'unscored_answer_observations':len(unscored),
            'metrics':metrics,'agreement':measure_metric(agreement,'agreement'),
            'disagreements':disagreements,'single_fact_exceptions':exceptions,'unscored':unscored,
            'controls':[x for x in scored if not x['primary']],'annotation_sources':provenance,
            'scoring_scope':'answer body only; immutable exact answer + human-frozen fact hashes; no consensus merging'}

def qa(root: Path, stage: str, partition: str) -> dict:
    require_gate(root,stage);plan=verify_plan(root,stage)
    folder=root/f'evals/project2-v1/{stage}'
    if partition=='held-out':
        tune=folder/'qa-tune/summary.json'
        if not tune.is_file() or json.loads(tune.read_text(encoding='utf-8')).get('repeats')!=3:raise ValueError('Tune QA evaluation must finish before held-out')
        receipt=folder/'heldout_receipt.json'
        if receipt.exists():raise ValueError('Held-out invocation already consumed; never rerun')
        from evaluation_protocol.storage import ledger
        event=ledger('stage_started','project2-'+stage+'-v031',config='project2-v031',scope='quick',planned_repeats=3,
                     stage_plan_sha256=digest(folder/'stage.plan.json'))
        save(receipt,{'stage':stage,'status':'started','heldout_stage_calls_project2':1,'heldout_repetitions_project2':0,'planned_repeats':3,
                      'global_ledger_entry_sha256':event['entry_sha256'],
                      'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'stage_plan_sha256':digest(folder/'stage.plan.json')})
    questions=select_questions(root,partition,stage)
    tasks=[{'question_id':x['record']['QUESTION_ID'],'group_sha256':x['group_sha256'],'body':online_question(x['record'])} for x in questions]
    def repeat_started(repeat):
        from evaluation_protocol.storage import ledger
        record_repeat(folder/'heldout_receipt.json',repeat)
        ledger('repeat_started','project2-'+stage+'-v031',repeat=repeat)
    target=folder/f'qa-{partition}';rows=invoke(root,tasks,target/'requests.jsonl',stage,repeat_started if partition=='held-out' else None)
    # Gold first enters here, after inference; it never reaches the application.
    from evaluation_protocol.runner import document_id, body_f1
    by_id={x['record']['QUESTION_ID']:x['record'] for x in questions};primary=set(json.loads((root/'splits.json').read_text(encoding='utf-8'))['partitions'][partition]['quick_question_ids'])
    for row in rows:
        record=by_id[row['question_id']];data=row['result'] or {};rag=data.get('workers',{}).get('rag',{})
        payload=rag.get('payload',{});trace=payload.get('trace',{});pipeline=payload.get('pipeline',{})
        ids=retrieved_ids(rag)
        # Parent-stage ranks are intentionally never substituted for v0's pipeline ranks.
        target_id=record['DOCUMENT'] if record['ANSWERABLE']=='Y' else None
        sources=payload.get('sources',[]);answer=payload.get('answer','')
        row.update({'label':record['ANSWERABLE'],'primary':row['question_id'] in primary,
                    'recall_at_5':int(target_id in [document_id(x) for x in ids[:5]]) if target_id else None,
                    'recall_at_10':int(target_id in [document_id(x) for x in ids[:10]]) if target_id else None,
                    'mrr':next((1/i for i,x in enumerate(ids,1) if document_id(x)==target_id),0) if target_id else None,
                    'retrieval_rank_stage':pipeline.get('stage'),
                    'correct_document_cited':int(any(document_id(x['chunk_id'])==target_id for x in sources)) if target_id else None,
                    'body_token_f1':body_f1(answer,record['ANSWER']) if target_id else None,
                    'n_refusal_proxy':int(rag.get('status')=='no_data') if not target_id else None,
                    'complete':int(rag.get('status')=='completed'),'partial':int(rag.get('status')=='partial'),
                    'attempts':data.get('usage',{}).get('attempts'),'llm_calls':data.get('usage',{}).get('llm_calls')})
    save(target/'scored.json',rows)
    base=json.loads((root/f'evals/protocol_v0/runs/baseline-v0-quick/{partition}/runs.json').read_text(encoding='utf-8'))
    lookup={(x['question_id'],x['repeat']):x for x in base};declines=[]
    for row in rows:
        old=lookup.get((row['question_id'],row['repeat']))
        if old:
            for key in ('recall_at_5','recall_at_10','mrr','correct_document_cited','n_refusal_proxy','body_token_f1'):
                if old.get(key) is not None and row.get(key) is not None and row[key]<old[key]:declines.append({'question_id':row['question_id'],'repeat':row['repeat'],'metric':key,'v0':old[key],'current':row[key]})
    chosen=[x for x in rows if x['primary']]
    metrics={key:measure_metric(chosen,key,binary=key not in {'mrr','body_token_f1','elapsed_seconds','attempts','llm_calls'}) for key in ('recall_at_5','recall_at_10','mrr','correct_document_cited','n_refusal_proxy','complete','partial','body_token_f1','elapsed_seconds','attempts','llm_calls')}
    value={'stage':stage,'partition':partition,'repeats':3,'metrics':metrics,'regression_items':declines,
           'controls':[x for x in rows if not x['primary']],'required_facts':reuse_fact_ratings(root,partition,rows),
           'source_sha256':digest(target/'requests.jsonl'),'stage_plan_sha256':digest(folder/'stage.plan.json'),
           'official_N_limitation':'N concerns original candidate corpus; refusal proxy is not full-corpus absence proof',
           'historical_exposure':json.loads((root/'splits.json').read_text(encoding='utf-8'))['historical_exposure']}
    save(target/'summary.json',value)
    if partition=='held-out':
        receipt=folder/'heldout_receipt.json';data=json.loads(receipt.read_text(encoding='utf-8'))
        data.update({'status':'completed','summary_sha256':digest(target/'summary.json'),'requests':len(rows)})
        save(receipt,data)
        from evaluation_protocol.storage import ledger
        ledger('stage_finished','project2-'+stage+'-v031',summary_sha256=digest(target/'summary.json'),status='completed')
    return value

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--stage',choices=sorted(STAGES),default='ch12')
    ap.add_argument('--register',action='store_true');ap.add_argument('--business',action='store_true');ap.add_argument('--qa-partition',choices=['tune','held-out']);args=ap.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    if args.register:register(ROOT,args.stage);LOGGER.info('Stage configuration locked')
    if args.business:business(ROOT,args.stage)
    if args.qa_partition:qa(ROOT,args.stage,args.qa_partition)
