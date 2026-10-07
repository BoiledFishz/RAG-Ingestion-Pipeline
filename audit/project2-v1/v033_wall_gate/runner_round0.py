"""Actual default API deadline fault injection; keep original S07 predicates."""
from __future__ import annotations
import asyncio
import csv
import json
import logging
import sys
import threading
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'enterprise-ai-agent'))
from project2_v031_calibration import HostGuard,save,digest
from run_project2_ch12_gate import Blackhole,HoldHTTP
from run_project2_v03_gate import check_consistency,read_matrix
FOLDER=ROOT/'audit/project2-v1/v033_wall_gate'
def run():
    from api.project2_main import create_app
    from agents.project2.policy import TrustedContext
    from fastapi.testclient import TestClient
    from agents.project2.budget import read_frozen_limits
    if FOLDER.exists():raise ValueError('Registered fault records cannot be overwritten')
    FOLDER.mkdir()
    cases={x['scenario_id']:x for x in csv.DictReader((ROOT/'specs/project2/v0.3.3/acceptance_scenarios.csv').open(encoding='utf-8-sig'))}
    def body(sid):return {k:v for k,v in json.loads(cases[sid]['input_source_and_selection']).items() if k!='sample_id'}
    save(FOLDER/'plan.json',{'spec_version':'v0.3.3','budget':read_frozen_limits(),'scenario_ids':['AC12-05','AC12-16'],
         'repeats':3,'queries_sha256':{k:digest(ROOT/'specs/project2/v0.3.3/acceptance_scenarios.csv') for k in ('AC12-05','AC12-16')},
         'AC12-05_fault':'original planned HTTP dispatch cancellation: suspend before effective dependency result, no fabricated corpus/count',
         'AC12-16_fault':'real localhost model HTTP blackhole; actual counted HTTP sends',
         'matrix_unchanged':True,'heldout_calls':0,'script_sha256':digest(Path(__file__))})
    owner=TrustedContext('wall-owner','local',frozenset({'full'}),frozenset({'document_count','compare_document_counts','rag_explain'}))
    rows=[];matrix=read_matrix(ROOT,'v0.3.1')
    with HostGuard(FOLDER/'power'):
        app=create_app(credentials={'wall-token':owner})
        cancelled=[]
        async def stalled(*args):
            try:await asyncio.sleep(120)
            except asyncio.CancelledError:cancelled.append(time.monotonic());raise
        app.state.supervisor.run=stalled
        with TestClient(app) as client:
            save(FOLDER/'startup_ac12_05.json',app.state.rag_runtime.startup_observation)
            for repeat in (1,2,3):
                start=time.monotonic();r=client.post('/v1/project2/analysis',headers={'Authorization':'Bearer wall-token'},json=body('AC12-05')).json();elapsed=time.monotonic()-start
                valid=check_consistency(r,matrix)['passed'] and r['status']=='timeout' and all(x['status']=='timeout' for x in r['workers'].values()) and len(cancelled)==repeat and r['usage']['attempts']==0 and 89<=elapsed<100
                row={'scenario_id':'AC12-05','repeat':repeat,'result':r,'elapsed_seconds':elapsed,'passed':valid,'dispatch_cancelled':len(cancelled)==repeat,'evidence_type':'故障注入','budget_seconds':90}
                rows.append(row);save(FOLDER/'observations.json',rows);logging.info('AC12-05 repeat%d passed=%s %.3fs',repeat,valid,elapsed)
        server=Blackhole(('127.0.0.1',0),HoldHTTP);server.finished=threading.Event();server.received=0
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            app=create_app(credentials={'wall-token':owner});app.state.rag_runtime.environment['AGENT_OLLAMA_URL']=f'http://127.0.0.1:{server.server_address[1]}'
            with TestClient(app) as client:
                save(FOLDER/'startup_ac12_16.json',app.state.rag_runtime.startup_observation)
                for repeat in (1,2,3):
                    ready_start=time.monotonic()
                    while not client.get('/healthz').json()['ready']:
                        if time.monotonic()-ready_start>180:raise TimeoutError('Readiness never recovered')
                        time.sleep(.1)
                    start=time.monotonic();r=client.post('/v1/project2/analysis',headers={'Authorization':'Bearer wall-token'},json=body('AC12-16')).json();elapsed=time.monotonic()-start
                    valid=check_consistency(r,matrix)['passed'] and r['workers']['rag']['status']=='timeout' and r['workers']['database']['status']=='completed' and r['usage']['llm_calls']>=1 and r['usage']['estimated_tokens'] is None and app.state.rag_runtime.cleanup_observation.get('mode')=='owned_force_cancel' and 89<=elapsed<100
                    row={'scenario_id':'AC12-16','repeat':repeat,'result':r,'elapsed_seconds':elapsed,'passed':valid,'received_http_attempts':server.received,'cancel_evidence':app.state.rag_runtime.cleanup_observation,'evidence_type':'故障注入','budget_seconds':90}
                    rows.append(row);save(FOLDER/'observations.json',rows);logging.info('AC12-16 repeat%d passed=%s %.3fs',repeat,valid,elapsed)
        finally:server.finished.set();server.shutdown();server.server_close();thread.join(timeout=2)
    result={'status':'passed' if len(rows)==6 and all(x['passed'] for x in rows) else 'failed','checks':rows,'budget_seconds':90,'heldout_calls':0,'evidence_type':'故障注入','scope':'Chap12 wall-related checks only; S14 remains failed'}
    save(FOLDER/'gate.json',result)
    print('Chap12 wall gate: '+result['status']+f" {sum(x['passed'] for x in rows)}/{len(rows)}")
    return 0 if result['status']=='passed' else 1
if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    raise SystemExit(run())
