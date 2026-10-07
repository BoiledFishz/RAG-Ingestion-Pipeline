"""Actual API subprocess stop/restart, unchanged-budget resume and Trace gate."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from project2_v031_calibration import HostGuard
from summarize_project2 import stage_verdict

LOGGER=logging.getLogger(__name__)
REQUIRED={'real_subprocess_restart','same_run_id','completed_database_skipped','budget_not_reset',
          'unknown_run_rejected','illegal_state_rejected','owner_read_resume_isolation','revocation_rechecked',
          'real_sqlite_fault_located_by_trace','parent_child_trace','unchanged_native_answer_body',
          'runtime_contract_tests','frozen_budget_and_baseline','heldout_reuse_only','read_only_policy_unregistered_publish'}


def read(path: Path):return json.loads(path.read_text(encoding='utf-8'))


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def sha(path: Path):return hashlib.sha256(path.read_bytes()).hexdigest()


def http(port: int, route: str, *, body=None, token='gate-owner-token', timeout=50) -> tuple[int,dict]:
    request=urllib.request.Request(f'http://127.0.0.1:{port}'+route,
                data=json.dumps(body).encode() if body is not None else None,
                headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
    try:
        with urllib.request.urlopen(request,timeout=timeout) as stream:return stream.status,json.load(stream)
    except urllib.error.HTTPError as error:return error.code,json.load(error)


class Server:
    def __init__(self, root: Path, folder: Path, name: str, *, fault=False):
        self.root=root;self.folder=folder;self.name=name;self.fault=fault;self.process=None
        self.log_path=folder/(name+'.log');self.handle=None
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0));self.port=listener.getsockname()[1]

    def start(self):
        self.handle=self.log_path.open('x',encoding='utf-8')
        arguments=[sys.executable,str(self.root/'scripts/project2_runtime_server.py'),
                   '--port',str(self.port),'--state-directory',str(self.folder/'state')]
        if self.fault:arguments+=['--fault-database-schema']
        environment={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONUNBUFFERED':'1'}
        self.process=subprocess.Popen(arguments,cwd=self.root,stdout=self.handle,stderr=subprocess.STDOUT,
                                      env=environment,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        started=time.monotonic()
        while time.monotonic()-started<120:
            if self.process.poll() is not None:raise RuntimeError('API subprocess exited before readiness')
            try:
                code,body=http(self.port,'/healthz',timeout=1)
                if code==200 and body.get('ready'):return
            except (OSError,TimeoutError):pass
            time.sleep(.1)
        raise TimeoutError('API readiness timeout')

    def stop(self):
        if self.process and self.process.poll() is None:
            if os.name=='nt':
                subprocess.run(['taskkill.exe','/PID',str(self.process.pid),'/T','/F'],capture_output=True,
                               creationflags=subprocess.CREATE_NO_WINDOW,timeout=10,check=False)
            else:self.process.terminate()
            self.process.wait(timeout=10)
        if self.handle:self.handle.close()


def registered_request(root: Path, scenario: str) -> dict:
    rows=csv.DictReader((root/'specs/project2/v0.3.1/acceptance_scenarios.csv').open(encoding='utf-8-sig',newline=''))
    row=next(x for x in rows if x['scenario_id']==scenario)
    return {key:value for key,value in json.loads(row['input_source_and_selection']).items() if key!='sample_id'}


def native(root: Path, folder: Path) -> dict:
    server=Server(root,folder,'before_stop');servers=[server];observation={'evidence_type':'真实运行','processes':[]}
    try:
        server.start();observation['processes'].append(server.process.pid)
        result=[]
        def request():
            try:result.append(http(server.port,'/v2/project2/analysis',body=registered_request(root,'AC13-01')))
            except Exception as error:result.append({'interrupted_client':type(error).__name__})
        thread=threading.Thread(target=request,daemon=True);thread.start()
        checkpoint=None;started=time.monotonic()
        while time.monotonic()-started<35:
            for path in (folder/'state').glob('*.json'):
                current=read(path)
                if (current.get('nodes',{}).get('database') or {}).get('status')=='completed' and current['budget']['llm_calls']>=1 and current['lifecycle']=='running':
                    checkpoint=current;break
            if checkpoint:break
            if not thread.is_alive():raise RuntimeError('Request ended before interrupted checkpoint was captured')
            time.sleep(.05)
        if checkpoint is None:raise RuntimeError('No completed DB plus consumed model attempt checkpoint')
        server.stop();thread.join(timeout=5)
        path=folder/'state'/(checkpoint['run_id']+'.json');checkpoint=read(path)
        save(folder/'before_restart_checkpoint.json',checkpoint)
        new=Server(root,folder,'after_restart');servers.append(new);new.start()
        observation['processes'].append(new.process.pid)
        code,resumed=http(new.port,'/v2/project2/runs/'+checkpoint['run_id']+'/resume',body={})
        save(folder/'resumed_response.json',resumed)
        trace_code,trace=http(new.port,'/v2/project2/runs/'+checkpoint['run_id']+'/trace')
        save(folder/'resume_trace.json',trace)
        events=trace.get('events',[])
        after=read(path)
        unknown=http(new.port,'/v2/project2/runs/'+'0'*32+'/resume',body={})
        other_read=http(new.port,'/v2/project2/runs/'+checkpoint['run_id'],token='gate-other-token')
        other_resume=http(new.port,'/v2/project2/runs/'+checkpoint['run_id']+'/resume',body={},token='gate-other-token')
        revoked=http(new.port,'/v2/project2/runs/'+checkpoint['run_id'],token='gate-revoked-token')
        illegal={**after,'lifecycle':'unregistered_lifecycle'};save(path,illegal)
        illegal_response=http(new.port,'/v2/project2/runs/'+checkpoint['run_id']+'/resume',body={})
        save(path,after)  # Controlled fault injection restored; frozen corpus/evidence untouched.
        log=new.log_path.read_text(encoding='utf-8')
        body_hash=hashlib.sha256(resumed.get('answer','').encode()).hexdigest()
        observation.update(checkpoint=checkpoint,after_budget=after['budget'],response_status=code,
            real_subprocess_restart=len(set(observation['processes']))==2 and server.process.poll() is not None,
            same_run_id=code==200 and resumed.get('run_id')==checkpoint['run_id'] and resumed.get('status')=='completed',
            completed_database_skipped=any(x['stage']=='database' and x.get('skipped') for x in events),
            budget_not_reset=after['budget']['attempts']>=checkpoint['budget']['attempts'] and after['budget']['llm_calls']>=checkpoint['budget']['llm_calls']
                  and after['budget']['absolute_deadline']==checkpoint['budget']['absolute_deadline'],
            unknown_run_rejected=unknown[0]==404 and unknown[1].get('error')=='unknown_run',
            illegal_state_rejected=illegal_response[0]==409 and illegal_response[1].get('error')=='illegal_state',
            owner_read_resume_isolation=other_read[0]==403 and other_resume[0]==403 and 'result' not in other_read[1],
            revocation_rechecked=revoked[0]==403,
            parent_child_trace=trace_code==200 and any(x['span_id']==checkpoint['run_id'] and x['parent_span_id'] is None for x in events)
                and all(x['parent_span_id'] is None or x['parent_span_id'] in {event['span_id'] for event in events} for x in events)
                and len({x['request_id'] for x in events})>=2,
            unchanged_native_answer_body=bool(resumed.get('answer')) and ('sha256='+body_hash) in log,
            client_interruption=result)
        new.stop()
        fault=Server(root,folder,'sqlite_fault',fault=True);servers.append(fault);fault.start()
        code,failed=http(fault.port,'/v2/project2/analysis',body=registered_request(root,'AC13-05'))
        save(folder/'fault_response.json',failed)
        code,trace=http(fault.port,'/v2/project2/runs/'+failed['run_id']+'/trace')
        save(folder/'fault_trace.json',trace)
        # Locate without reading the query or Worker answer, using Trace alone.
        diagnosis=[{'stage':x['stage'],'error_category':x.get('error_category'),'status':x['status']}
                   for x in trace.get('events',[]) if x.get('error_category')]
        save(folder/'trace_only_diagnosis.json',{'diagnosis':diagnosis,'query_or_answer_read':False})
        observation['real_sqlite_fault_located_by_trace']=any(x['stage']=='database' and x['error_category']=='database_error' for x in diagnosis)
        observation['fault_status']=failed.get('status')
        observation['fault_expected_s07']=failed.get('status')=='partial' and failed['workers']['rag']['status']=='completed' and failed['workers']['database']['status']=='failed'
        observation['real_sqlite_fault_located_by_trace'] &= observation['fault_expected_s07']
        forbidden=registered_request(root,'AC13-06');forbidden['analysis_operation']='publish'
        code,invalid=http(fault.port,'/v2/project2/analysis',body=forbidden)
        observation['read_only_policy_unregistered_publish']=code==422 and invalid.get('status')=='failed' and invalid['usage']['attempts']==0
        save(folder/'readonly_contract.json',{'http_status':code,'status':invalid.get('status'),'attempts':invalid.get('usage',{}).get('attempts'),
                                             'fake_publish_executed':False,'evidence_type':'契约测试(Mock)'})
        return observation
    finally:
        for server in servers:server.stop()


def run_gate(root: Path=ROOT, repair_round: int=0) -> dict:
    from project2_continuation_report import authority
    authorized=authority(root)
    if not authorized:raise ValueError('Continuation authority required while S14 is failed')
    if repair_round not in (0,1,2):raise ValueError('At most two repairs')
    folder=root/f'audit/project2-v1/ch13_round{repair_round}'
    if folder.exists():raise ValueError('Gate round already registered; preserve it')
    folder.mkdir(parents=True)
    # Register scenarios/criteria BEFORE any response is observed.
    save(folder/'plan.json',{'chapter':'Chap13','repair_round':repair_round,'checks':sorted(REQUIRED),
                            'scenario_ids':['AC13-01','AC13-02','AC13-03','AC13-04','AC13-05','AC13-06'],
                            'heldout_calls':0,'scope':'tune registered originals only','script_sha256':sha(Path(__file__)),
                            'budget_sha256':sha(root/'evals/project2-v1/calibration_v031/budget_frozen.json'),
                            'authorization_sha256':authorized['sha256'],
                            'runtime_files':{path.relative_to(root).as_posix():sha(path) for path in (
                                root/'enterprise-ai-agent/agents/project2/service_runtime.py',
                                root/'enterprise-ai-agent/api/project2_runtime_main.py',
                                root/'scripts/project2_runtime_server.py')}})
    observations={};error=None
    try:
        with HostGuard(folder/'power'):observations=native(root,folder)
    except Exception as exc:
        LOGGER.exception('Chap13 native gate failed')
        error={'category':type(exc).__name__,'detail':str(exc)[:400]}
    save(folder/'native_observations.json',{'observations':observations,'error':error})
    from run_project2_ch12_gate import junit_pass
    testfile=folder/'runtime_contract.xml'
    arguments=[sys.executable,'-m','pytest','enterprise-ai-agent/tests/project2/test_runtime.py',
               'enterprise-ai-agent/tests/project2/test_v03_contracts.py','enterprise-ai-agent/tests/project2/test_v031_lineage.py',
               '-q','--junitxml='+str(testfile)]
    result=subprocess.run(arguments,cwd=root,capture_output=True,text=True,encoding='utf-8')
    (folder/'runtime_contract.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    observations['runtime_contract_tests']=result.returncode==0 and junit_pass(testfile)
    baseline=read(root/'evals/protocol_v0/baseline_v0.config.json')
    from project2_v031_budget import validate_selected_batch
    limits,_=validate_selected_batch(root)
    observations['frozen_budget_and_baseline']=limits['status']=='selected' and all(sha(root/name)==value for name,value in baseline['sut']['files'].items())
    receipt=root/'evals/project2-v1/ch12/heldout_receipt.json';held=read(receipt)
    observations['heldout_reuse_only']=held['heldout_stage_calls_project2']==1 and held['heldout_repetitions_project2']==3
    failure=[name for name in sorted(REQUIRED) if observations.get(name) is not True]
    checks=[{'check':name,'expected':True,'observed':observations.get(name) is True,
             'status':'passed' if observations.get(name) is True else 'failed',
             'evidence_type':'契约测试(Mock)' if name=='runtime_contract_tests' else '故障注入' if name in {'real_subprocess_restart','real_sqlite_fault_located_by_trace','illegal_state_rejected'} else '真实运行',
             'evidence_file':(folder/'native_observations.json').relative_to(root).as_posix()} for name in sorted(REQUIRED)]
    report={'stage':'Chap13','status':'failed' if failure else 'passed','system_gate_executed':True,'gate_scope':'system_gate',
            'checks':checks,'failure_items':failure,'repair_rounds':repair_round,
            'stop_reason':('Chap13两轮修复后仍失败：'+','.join(failure)) if failure and repair_round==2 else None,
            's14_status':'未通过','heldout_new_calls':0,'heldout_reuse_receipt_sha256':sha(receipt),
            'generation_path':'unchanged frozen generator; Runtime persistence/authorization only',
            'plan_sha256':sha(folder/'plan.json'),'native_error':error}
    if stage_verdict(report)!=report['status']:raise ValueError('Gate claim differs from machine predicate')
    save(folder/'gate.json',report);save(root/'audit/project2-v1/v031_chap13_gate.json',report)
    if not failure:
        target=root/'evals/project2-v1/ch13';target.mkdir(exist_ok=True)
        save(target/'heldout_reuse.json',{'source':receipt.relative_to(root).as_posix(),'source_sha256':sha(receipt),
                'new_stage_calls':0,'new_repeats':0,'rule':'generation path unchanged; reuse original Chap12 record, including quality limitations; no held-out bodies read'})
    return report


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repair-round',required=True,type=int);args=ap.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    report=run_gate(ROOT,args.repair_round);LOGGER.info('Chap13 %s failed=%s',report['status'],report['failure_items'])
    raise SystemExit(0 if report['status']=='passed' else 1)
