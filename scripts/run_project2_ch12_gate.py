"""Chapter 12 full engineering gate; no claimed pass can substitute a check."""
from __future__ import annotations
import argparse
import asyncio
import csv
import json
import logging
import socketserver
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from project2_v031_calibration import ROOT, HostGuard, digest, save
from project2_v031_budget import validate_selected_batch
from run_project2_v03_gate import check_consistency, read_matrix
from check_project2_v03_counts import check as count_check

LOGGER=logging.getLogger(__name__)
REQUIRED={'budget_frozen','frozen_v0_unchanged','component_checks','independent_count_recomputation',
          'AC12-01','AC12-23(a)','AC12-02','AC12-10','AC12-11','AC12-13','AC12-16','36_S07_cells','old_multiagent_regression'}

def allowed_repair(native_rounds: int, full_rounds: int) -> bool:
    return native_rounds in (0,1,2) and full_rounds in (0,1,2) and native_rounds+full_rounds<=2


def verdict(checks: list[dict]) -> str:
    names=[x['check'] for x in checks]
    valid=set(names)==REQUIRED and len(names)==len(REQUIRED)
    return 'passed' if valid and all(x.get('expected') is True and x.get('observed') is True and x.get('status')=='passed' for x in checks) else 'failed'


def junit_pass(path: Path) -> bool:
    if not path.is_file():return False
    cases=ET.parse(path).getroot().findall('.//testcase')
    return bool(cases) and all(x.find('failure') is None and x.find('error') is None and x.find('skipped') is None for x in cases)


def registration(root: Path) -> dict:
    return {'version':'project2-ch12-extras-v1','partition':'tune','repeats':3,
          'spec_manifest_sha256':digest(root/'specs/project2/v0.3.1/version_manifest.json'),
          'variants':[{'name':'default','environment':{'RETRIEVAL_CANDIDATE_K':'30','RRF_RANK_CONSTANT':'60'}},
                      {'name':'candidate45_rrf30','environment':{'RETRIEVAL_CANDIDATE_K':'45','RRF_RANK_CONSTANT':'30'}},
                      {'name':'candidate60_rrf100','environment':{'RETRIEVAL_CANDIDATE_K':'60','RRF_RANK_CONSTANT':'100'}}],
          'selection':'AC12-02/10/11/13/16 original registered queries, never substitute from outputs',
          'fault':'local HTTP blackhole generation dependency; real original query, counted send attempt; no artificial corpus',
          'gold_fields_online':False,'heldout_calls':0}


class Blackhole(socketserver.ThreadingTCPServer):
    allow_reuse_address=True;daemon_threads=True


class HoldHTTP(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            self.request.settimeout(2);self.request.recv(65536)
            self.server.received+=1
            self.server.finished.wait(120)
        except OSError:pass


def extras(root: Path, number: int, protocol: dict) -> dict:
    sys.path.insert(0,str(root/'enterprise-ai-agent'))
    from agents.project2.policy import TrustedContext
    from agents.project2.budget import read_frozen_limits
    from api.project2_main import create_app
    from tools.techqa_document_query import DatabaseWorker
    from fastapi.testclient import TestClient
    cases={x['scenario_id']:x for x in csv.DictReader((root/'specs/project2/v0.3.1/acceptance_scenarios.csv').open(encoding='utf-8-sig'))}
    def request(case):return {k:v for k,v in json.loads(cases[case]['input_source_and_selection']).items() if k!='sample_id'}
    owner=TrustedContext('full-gate-owner','local',frozenset({'full'}),frozenset({'document_count','compare_document_counts','rag_explain'}))
    matrix=read_matrix(root,'v0.3.1');rows=[]
    preflight=json.loads((root/'audit/project2-v1/preflight_report.json').read_text(encoding='utf-8'))
    for variant in protocol['variants']:
        app=create_app(credentials={'local-gate':owner});app.state.rag_runtime.environment.update(variant['environment'])
        with TestClient(app) as client:
            queue=['AC12-13'] if variant['name']!='default' else ['AC12-02','AC12-10','AC12-11','AC12-13']
            for case in queue:
                for repeat in (1,2,3):
                    app.state.supervisor.database=DatabaseWorker(root/'.rag_data/techqa_full.sqlite',inject_timeout_group=1 if case=='AC12-11' else None)
                    body=request(case)
                    if case=='AC12-10':body['sample_limit']=(0,1,10)[repeat-1]
                    started=time.monotonic();result=client.post('/v1/project2/analysis',headers={'Authorization':'Bearer local-gate'},json=body).json()
                    status=check_consistency(result,matrix)
                    pair=cases[case]['expected_worker_states']
                    expected=tuple(item.split('=')[1] for item in pair.split(';'))
                    valid=status['passed'] and (status['rag_status'],status['db_status'])==expected
                    db=result['workers']['database']['payload'];sample=cases[case]['input_sample_id']
                    reference=preflight['sample_measurements'][sample]
                    if case=='AC12-02':valid=valid and db['measurement_complete'] is True and db['groups'][0]['count']==0
                    else:
                        observed=[x['count'] for x in db['groups']]
                        expected_counts=reference['counts'] if case!='AC12-11' else [reference['counts'][0],None]
                        valid=valid and observed==expected_counts
                        if case=='AC12-11':valid=valid and db['intersection'] is None and db['delta_a_minus_b'] is None
                    if status.get('rag_status')=='completed':
                        lineage=result['workers']['rag']['payload'].get('source_lineage',[])
                        valid=valid and bool(lineage) and all(x['candidate_rank'] and x['start_char'] is not None and x['end_char']>x['start_char'] for x in lineage)
                    rows.append({'scenario_id':case,'variant':variant,'repeat':repeat,'passed':bool(valid),
                                 'result':result,'elapsed_seconds':time.monotonic()-started,'evidence_type':'故障注入' if case=='AC12-11' else '真实运行'})
                    LOGGER.info('extra %s %s repeat%d passed=%s',case,variant['name'],repeat,valid)
    server=Blackhole(('127.0.0.1',0),HoldHTTP);server.finished=threading.Event();server.received=0
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        app=create_app(credentials={'local-gate':owner});app.state.rag_runtime.environment['AGENT_OLLAMA_URL']=f'http://127.0.0.1:{server.server_address[1]}'
        with TestClient(app) as client:
            for repeat in (1,2,3):
                started=time.monotonic();result=client.post('/v1/project2/analysis',headers={'Authorization':'Bearer local-gate'},json=request('AC12-16')).json()
                status=check_consistency(result,matrix)
                valid=status['passed'] and status['rag_status']=='timeout' and status['db_status']=='completed' and result['usage']['llm_calls']>=1 and result['usage']['estimated_tokens'] is None and not app.state.rag_runtime.active
                rows.append({'scenario_id':'AC12-16','repeat':repeat,'passed':bool(valid),'result':result,
                             'received_http_attempts':server.received,'elapsed_seconds':time.monotonic()-started,'evidence_type':'故障注入'})
    finally:server.finished.set();server.shutdown();server.server_close();thread.join(timeout=2)
    expected_rows=3*(4+1+1+1)
    report={'complete':len(rows)==expected_rows,'expected_rows':expected_rows,'rows':rows,'protocol_sha256':digest(root/'evals/project2-v1/ch12_gate_preregistration.json')}
    save(root/f'audit/project2-v1/v031_ch12_extras_round{number}.json',report)
    return report


def run(root: Path, number: int) -> dict:
    if number not in (0,1,2):raise ValueError('Maximum two repair rounds')
    audit=root/'audit/project2-v1';target=audit/f'v031_ch12_gate_round{number}.json'
    if target.exists():raise ValueError('Finalized round; no replay')
    decision,batch=validate_selected_batch(root)
    sys.path.insert(0,str(root/'enterprise-ai-agent'))
    from agents.project2.budget import read_frozen_limits
    limits=read_frozen_limits(root)
    native=next((json.loads((audit/f'v031_native_gate_round{n}.json').read_text(encoding='utf-8')) for n in (2,1,0) if (audit/f'v031_native_gate_round{n}.json').is_file()),None)
    if not native or native['status']!='passed':raise ValueError('Native subgate has not passed; full gate must wait')
    if not allowed_repair(native['repair_rounds'],number):raise ValueError('Chapter 12 shared two-repair limit exhausted')
    path=root/'evals/project2-v1/ch12_gate_preregistration.json';protocol=json.loads(path.read_text(encoding='utf-8'))
    result=extras(root,number,protocol)
    selections=['tests/project2/test_db_worker.py','tests/project2/test_worker_independence.py','tests/project2/test_budget.py',
                'tests/project2/test_core.py::test_all_36_pairs_match_frozen_matrix','tests/project2/test_core.py::test_request_preserves_query_and_rejects_oracle_or_sql',
                'tests/project2/test_api.py','tests/project2/test_v03_contracts.py','tests/project2/test_v03_boundary.py',
                'tests/project2/test_v03_cancel_ownership.py','tests/project2/test_v031_lineage.py','tests/project2/test_data_contract.py',
                'tests/project2/test_shared_startup.py','tests/project2/test_process_tree.py','tests/project2/test_verified_budget_cache.py']
    junit=audit/f'v031_ch12_components_round{number}.junit.xml'
    process=subprocess.run([str(root/'.venv/Scripts/python.exe'),'-X','utf8','-m','pytest','-q',*selections,'--junitxml='+str(junit)],cwd=root/'enterprise-ai-agent',capture_output=True,text=True,encoding='utf-8')
    (audit/f'v031_ch12_components_round{number}.log').write_text(process.stdout+process.stderr,encoding='utf-8')
    counts=count_check(root,batch/'requests.jsonl');save(audit/'v031_independent_counts.json',counts)
    baseline=json.loads((root/'evals/protocol_v0/baseline_v0.config.json').read_text(encoding='utf-8'))
    observed={'budget_frozen':limits==decision['limits'],'frozen_v0_unchanged':all(digest(root/name)==sha for name,sha in baseline['sut']['files'].items()),
              'component_checks':process.returncode==0 and junit_pass(junit),'independent_count_recomputation':counts['status']=='passed',
              'AC12-01':next(x['observed'] for x in native['checks'] if x['check']=='AC12-01'),
              'AC12-23(a)':next(x['observed'] for x in native['checks'] if x['check']=='AC12-23(a)'),
              '36_S07_cells':junit_pass(junit),'old_multiagent_regression':junit_pass(audit/'v031_multiagent_regression.junit.xml')}
    for case in ('AC12-02','AC12-10','AC12-11','AC12-13','AC12-16'):
        selected=[x for x in result['rows'] if x['scenario_id']==case]
        observed[case]=result['complete'] and len(selected)==(9 if case=='AC12-13' else 3) and all(x['passed'] for x in selected)
    checks=[{'check':name,'expected':True,'observed':bool(observed[name]),'status':'passed' if observed[name] else 'failed'} for name in sorted(REQUIRED)]
    report={'stage':'Chap12','spec_version':'v0.3.1','gate_scope':'system_gate','system_gate_executed':True,
            'status':verdict(checks),'checks':checks,'repair_rounds':number,'chapter_repair_rounds':native['repair_rounds']+number,'limits':limits,
            'failure_items':[x['check'] for x in checks if x['status']=='failed'],'heldout_stage_calls_project2':0,
            'engineering_gate_only':True,'comparison_and_heldout_pending':True,
            'evidence_files':[str(junit.relative_to(root)),f'audit/project2-v1/v031_ch12_extras_round{number}.json', 'audit/project2-v1/v031_independent_counts.json']}
    save(target,report);save(audit/'v031_chap12_gate.json',report)
    return report


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--register',action='store_true');ap.add_argument('--repair-round',type=int);args=ap.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    if args.register:
        path=ROOT/'evals/project2-v1/ch12_gate_preregistration.json';value=registration(ROOT)
        if path.exists() and json.loads(path.read_text(encoding='utf-8'))!=value:raise ValueError('Preregistered extras changed')
        if not path.exists():save(path,value)
        LOGGER.info('Registered extras SHA256=%s',digest(path))
    if args.repair_round is not None:
        with HostGuard(ROOT/f'audit/project2-v1/v031_ch12_power_round{args.repair_round}'):
            report=run(ROOT,args.repair_round)
        LOGGER.info('full_gate=%s failures=%s',report['status'],report['failure_items'])
        raise SystemExit(0 if report['status']=='passed' else 1)
