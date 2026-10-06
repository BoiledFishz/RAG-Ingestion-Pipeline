"""Authorized v0.3 native subgate; N quality is explicitly not a pass criterion."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import logging
import math
import random
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger(__name__)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def read_matrix(root: Path, version: str='v0.3') -> dict[tuple[str,str], str]:
    text = (root/'specs/project2'/version/'spec.md').read_text(encoding='utf-8')
    block = text.split('id="s07"',1)[1].split('id="s08"',1)[0]
    lines = [x for x in block.splitlines() if x.startswith('| ')]
    columns = [x.strip() for x in lines[0].strip('|').split('|')][1:]
    matrix = {}
    for line in lines[2:]:
        cells = [x.strip() for x in line.strip('|').split('|')]
        matrix.update({(cells[0],db): expected for db,expected in zip(columns,cells[1:])})
    if len(matrix) != 36:
        raise ValueError('Frozen S07 does not contain 36 cells')
    return matrix


def check_consistency(data: dict, matrix: dict) -> dict[str, Any]:
    try:
        rid = data['run_id']; workers = data['workers']
        rag,db = workers['rag'],workers['database']
        pair = (rag['status'],db['status'])
        state = pair in matrix and data['status'] == matrix[pair]
        traceable = bool(rid) and all(x['run_id'] == rid for x in (rag,db)) and {'attempts','llm_calls'} <= set(data['usage'])
        for worker in (rag,db):
            if worker['status'] in {'permission_denied','timeout','failed'}:
                traceable = traceable and bool(worker.get('error'))
        if rag['status'] in {'completed','partial','no_data'}:
            traceable = traceable and isinstance(rag.get('payload',{}).get('trace'),dict)
        if db['status'] in {'completed','partial','no_data'}:
            traceable = traceable and bool(db.get('payload',{}).get('groups'))
        return {'passed': bool(state and traceable), 'rag_status': pair[0], 'db_status': pair[1],
                'matrix_cell': f'S07[rag={pair[0]},db={pair[1]}]', 'expected_overall': matrix.get(pair),
                'observed_overall': data['status'], 'traceable': bool(traceable), 'run_id': rid}
    except (KeyError,TypeError):
        return {'passed': False, 'traceable': False, 'reason': 'invalid_or_untraceable_response'}


def wilson(n: int, d: int) -> list[float] | None:
    if not d: return None
    z=1.959963984540054; p=n/d; denominator=1+z*z/d
    center=(p+z*z/(2*d))/denominator
    margin=z*math.sqrt(p*(1-p)/d+z*z/(4*d*d))/denominator
    return [max(0,center-margin),min(1,center+margin)]


def quality(rows: list[dict[str,Any]]) -> dict[str, Any]:
    by_repeat = []
    for repeat in (1,2,3):
        selected = [x for x in rows if x['repeat']==repeat and x['cohort']=='N']
        counts = Counter(x.get('check',{}).get('rag_status','crash') for x in selected)
        by_repeat.append({'repeat':repeat, 'refusals':counts['no_data'], 'total':len(selected),
                          'wilson95':wilson(counts['no_data'],len(selected)), 'states':dict(counts)})
    total=sum(x['total'] for x in by_repeat); numerator=sum(x['refusals'] for x in by_repeat)
    unique = {x['query_sha256'] for x in rows if x['cohort']=='N'}
    clusters = []
    for query_hash in sorted(unique):
        cluster=[x for x in rows if x['cohort']=='N' and x['query_sha256']==query_hash]
        clusters.append((sum(x.get('check',{}).get('rag_status')=='no_data' for x in cluster),len(cluster)))
    rng=random.Random(20261005); boot=[]
    if clusters:
        for _ in range(10000):
            chosen=rng.choices(clusters,k=len(clusters)); boot.append(sum(x[0] for x in chosen)/sum(x[1] for x in chosen))
        boot.sort()
    rates=[x['refusals']/x['total'] for x in by_repeat if x['total']]
    return {'metric_is_gate':False,'numerator':numerator,'denominator':total,'wilson95_pooled_descriptive':wilson(numerator,total),
            'cluster_bootstrap95':[boot[249],boot[9749]] if boot else None, 'independent_query_clusters':len(unique),
            'mean':sum(rates)/len(rates) if rates else None,'range':[min(rates),max(rates)] if rates else None,'repeats':by_repeat,
            'baseline_v0_conclusion_unchanged':True,'project2_claims_quality_improvement':False,
            'scope_limitation':'Official N label covers original candidate documents, not absence of any full-corpus answer; accepted cases require independent applicability review.'}


def activate_budget(root: Path) -> None:
    folder=root/'evals/project2-v1/calibration_v03'
    from project2_v03_calibration import select_limits
    protocol=json.loads((folder/'protocol.json').read_text(encoding='utf-8'))
    rows=[json.loads(x) for x in (folder/'requests.jsonl').read_text(encoding='utf-8').splitlines()]
    expected={(path,sample['sample_id'],repeat) for path in protocol['paths'] for sample in protocol['samples'] for repeat in range(1,4)}
    observed=[(x['path'],x['sample_id'],x['repeat']) for x in rows]
    if len(observed)!=len(expected) or set(observed)!=expected:
        raise ValueError('Incomplete or duplicate measurements; cannot activate budget')
    paths={path:select_limits([x for x in rows if x['path']==path]) for path in protocol['paths']}
    if any(x['status']!='selected' for x in paths.values()):
        raise ValueError('Calibration censored or structural fuse; stop, do not enlarge budget')
    report=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
    limits={key:max(x['limits'][key] for x in paths.values()) for key in ('attempts','llm_calls','seconds')}
    if report['status']!='selected' or report['limits']!=limits:
        raise ValueError('Limits differ from independent measurement recomputation')
    data={'version':'project2-v0.3-budget-v1','status':'frozen','limits':limits,
          'calibration_manifest_sha256':sha(folder/'frozen_manifest.json'),
          'spec_manifest_sha256':sha(root/'specs/project2/v0.3/version_manifest.json')}
    target=folder/'budget_frozen.json'
    if target.exists() and json.loads(target.read_text(encoding='utf-8'))!=data:
        raise ValueError('Budget profile already frozen; cannot overwrite')
    if not target.exists(): write(target,data)
    LOGGER.info('Budget frozen SHA256=%s limits=%s',sha(target),limits)


def run(root: Path, repair_round: int, resume: bool, *, version: str='v0.3',
        calibration_folder: Path | None=None, prefix: str='v03', guard: Any=None) -> dict[str,Any]:
    if repair_round not in (0,1,2): raise ValueError('Maximum two repair rounds')
    sys.path.insert(0,str(root/'enterprise-ai-agent'))
    from api.project2_main import create_app
    from agents.project2.policy import TrustedContext
    from fastapi.testclient import TestClient
    from agents.project2.budget import read_frozen_limits
    folder=calibration_folder or root/'evals/project2-v1/calibration_v03'
    if not (folder/'budget_frozen.json').is_file(): raise ValueError('No calibrated production profile; native gate prohibited')
    limits=read_frozen_limits(root)
    protocol=json.loads((folder/'protocol.json').read_text(encoding='utf-8'))
    audit=root/'audit/project2-v1'; records_path=audit/f'{prefix}_native_requests_round{repair_round}.jsonl'
    target=audit/f'{prefix}_native_gate_round{repair_round}.json'
    if target.exists(): raise ValueError('Round already finalized; no rerun')
    if records_path.exists() and not resume: raise ValueError('Records exist; explicit resume only')
    rows=[json.loads(x) for x in records_path.read_text(encoding='utf-8').splitlines()] if records_path.exists() else []
    done={(x['cohort'],x['sample_id'],x['repeat']) for x in rows}
    scenes=list(csv.DictReader((root/'specs/project2'/version/'acceptance_scenarios.csv').open(encoding='utf-8-sig',newline='')))
    cases={x['scenario_id']:x for x in scenes}
    challenge=json.loads(cases['AC12-23']['input_source_and_selection'])
    challenge['query_sha256']=hashlib.sha256(challenge['query'].encode('utf-8')).hexdigest()
    completed=json.loads(cases['AC12-01']['input_source_and_selection'])
    completed['query_sha256']=hashlib.sha256(completed['query'].encode('utf-8')).hexdigest()
    queue=[('completed_probe',completed),*[('N',sample) for sample in protocol['n_samples']],('original_challenge',challenge)]
    matrix=read_matrix(root,version); token='local-v03-gate'
    owner=TrustedContext('native-gate-owner','local',frozenset({'full'}),frozenset({'document_count','compare_document_counts','rag_explain'}))
    try:
        with TestClient(create_app(credentials={token:owner})) as client:
            for cohort,sample in queue:
                for repeat in (1,2,3):
                    key=(cohort,sample['sample_id'],repeat)
                    if key in done: continue
                    if guard is not None: guard.ensure_running()
                    body={k:v for k,v in sample.items() if k not in {'sample_id','query_sha256'}}
                    started=time.monotonic(); data=None; error=None; http=None
                    try:
                        response=client.post('/v1/project2/analysis',headers={'Authorization':f'Bearer {token}'},json=body)
                        http=response.status_code; data=response.json(); check=check_consistency(data,matrix)
                        if cohort=='completed_probe':
                            check['passed']=check['passed'] and check['rag_status']=='completed' and check['db_status']=='completed'
                        check['passed']=check['passed'] and http in {200,422}
                    except Exception as exc:
                        error={'category':type(exc).__name__,'detail':str(exc)[:400]}; check={'passed':False,'traceable':False}
                    row={'cohort':cohort,'sample_id':sample['sample_id'],'query_sha256':sample['query_sha256'],'repeat':repeat,
                         'result':data,'exception':error,'http_status':http,'check':check,'elapsed_seconds':time.monotonic()-started,'evidence_type':'真实运行'}
                    with records_path.open('a',encoding='utf-8') as handle: handle.write(json.dumps(row,ensure_ascii=False)+'\n')
                    rows.append(row)
                    LOGGER.info('v03 gate %s %s repeat=%d check=%s progress=%d/%d',cohort,sample['sample_id'],repeat,check,len(rows),len(queue)*3)
    except Exception as exc:
        write(audit/f'{prefix}_native_startup_failure_round{repair_round}.json',{'status':'failed','exception':type(exc).__name__+':'+str(exc),'evidence_type':'真实运行','system_gate_executed':False})
        raise
    return finalize(root,repair_round,rows,len(queue)*3,limits,version=version,prefix=prefix)


def finalize(root: Path, repair_round: int, rows: list[dict], expected_requests: int, limits: dict,
             *, version: str='v0.3', prefix: str='v03') -> dict:
    audit=root/'audit/project2-v1';records_path=audit/f'{prefix}_native_requests_round{repair_round}.jsonl'
    target=audit/f'{prefix}_native_gate_round{repair_round}.json'
    if target.exists():raise ValueError('Round already finalized; no replacement')
    n_rows=[x for x in rows if x['cohort']=='N']
    complete=len(rows)==expected_requests and len({(x['cohort'],x['sample_id'],x['repeat']) for x in rows})==len(rows)
    completed_passed=all(x['check']['passed'] for x in rows if x['cohort']=='completed_probe') and sum(x['cohort']=='completed_probe' for x in rows)==3
    n_passed=len(n_rows)==183*3 and all(x['check']['passed'] for x in n_rows)
    checks=[{'check':'AC12-01','expected':True,'observed':completed_passed,'status':'passed' if completed_passed else 'failed'},
            {'check':'AC12-23(a)','expected':True,'observed':n_passed,'status':'passed' if n_passed else 'failed'}]
    report={'stage':'Chap12','spec_version':version,'gate_scope':'native_combination_subgate','system_gate_executed':False,
            'status':'passed' if complete and all(x['status']=='passed' for x in checks) else 'failed','checks':checks,
            'failure_items':[x['check'] for x in checks if x['status']!='passed'],'repair_rounds':repair_round,'complete':complete,
            'records_sha256':sha(records_path),'limits':limits,'heldout_stage_calls_project2':0,'heldout_repetitions_project2':0,
            'n_quality':quality(rows),'original_challenge':[x for x in rows if x['cohort']=='original_challenge'],
            'conformance':{'numerator':sum(x['check']['passed'] for x in n_rows),'denominator':len(n_rows),'wilson95':wilson(sum(x['check']['passed'] for x in n_rows),len(n_rows))}}
    write(audit/f'{prefix}_n_accepted_details.json',{'samples':[x for x in n_rows if x.get('check',{}).get('rag_status') in {'completed','partial'}],
          'baseline_v0_conclusion_unchanged':True,'not_independently_fact_adjudicated':True,'scope':'official candidate N label, full corpus retrieval'})
    write(target,report)
    return report


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate-budget',action='store_true'); parser.add_argument('--repair-round',type=int)
    parser.add_argument('--resume',action='store_true'); args=parser.parse_args()
    if args.activate_budget: activate_budget(ROOT)
    if args.repair_round is not None:
        report=run(ROOT,args.repair_round,args.resume); LOGGER.info('v03 subgate=%s',report['status'])
        return 0 if report['status']=='passed' else 1
    return 0


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    raise SystemExit(main())
