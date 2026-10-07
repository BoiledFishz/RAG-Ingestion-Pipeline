"""Identical 15-check Chap13 gate, with directly authorized cumulative-time accounting."""
from __future__ import annotations
import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import run_project2_ch13_gate as prior
from project2_v031_calibration import HostGuard
from summarize_project2 import stage_verdict
from run_project2_ch12_gate import junit_pass
_original_http=prior.http
def bounded_transport(*args,**kwargs):
    kwargs.setdefault('timeout',100)
    return _original_http(*args,**kwargs)
prior.http=bounded_transport
from project2_stage_eval import source_lock
read,save,sha,http=prior.read,prior.save,prior.sha,prior.http
REQUIRED=prior.REQUIRED

class TimedServer(prior.Server):
    def start(self):
        launched=time.time();super().start()
        path=self.folder/('startup_'+str(self.port)+'.json')
        data=read(path)
        data['parent_launch_wall_time']=launched
        data['process_launch_to_entry_seconds']=data['process_entry_wall_time']-launched
        data['parent_launch_to_ready_seconds']=time.time()-launched
        save(self.folder/(self.name+'_startup.json'),data)

def native(folder):
    prior.Server=TimedServer
    observation=prior.native(ROOT,folder)
    cp=read(folder/'before_restart_checkpoint.json')
    path=folder/'state'/(cp['run_id']+'.json');after=read(path)
    # The existing scenario/gate predicates remain. Only deadline comparator
    # changes from absolute equality to durable cumulative execution equality.
    a,b=cp['budget'],after['budget'];x,y=a['execution'],b['execution']
    numeric=(y['limit_seconds']==x['limit_seconds']==90 and y['lifetime_seconds']==900)
    cumulative=y['consumed_seconds']>=x['consumed_seconds'] and len(y['segments'])==len(x['segments'])+1
    preserved=all(y['segments'][i]['consumed_seconds']>=s['consumed_seconds'] for i,s in enumerate(x['segments']))
    attempts=b['attempts']>=a['attempts'] and b['llm_calls']>=a['llm_calls']
    # Both original AC13-02 expiry conditions use the same real saved run.
    server=TimedServer(ROOT,folder,'expiry_checks')
    try:
        server.start()
        expired=json.loads(json.dumps(after));expired['created_at']=time.time()-901;save(path,expired)
        code,lifetime=http(server.port,'/v2/project2/runs/'+cp['run_id']+'/resume',body={})
        exhausted=json.loads(json.dumps(after));execution=exhausted['budget']['execution']
        execution['segments'][-1]['consumed_seconds']+=90
        execution['consumed_seconds']=sum(s['consumed_seconds'] for s in execution['segments']);save(path,exhausted)
        code2,limit=http(server.port,'/v2/project2/runs/'+cp['run_id']+'/resume',body={})
        save(path,after)
        rejections={'lifetime':{'http_status':code,'response':lifetime},'cumulative':{'http_status':code2,'response':limit},
                    'evidence_type':'故障注入','source_run':cp['run_id']}
        save(folder/'expiry_rejections.json',rejections)
        reject=code==409 and code2==409 and lifetime.get('error')=='run_lifetime_exhausted' and limit.get('error')=='cumulative_execution_exhausted'
        reject &= all(r['status']=='timeout' and r['run_id']==cp['run_id'] and r['usage']['attempts']==b['attempts'] and r['usage']['llm_calls']==b['llm_calls'] for r in (lifetime,limit))
    finally:server.stop()
    observation['budget_not_reset']=numeric and cumulative and preserved and attempts and reject
    save(folder/'recovery_accounting_evidence.json',{'before':x,'after':y,'numeric_limits_unchanged':numeric,
        'attempts_preserved':attempts,'cumulative_not_reset':cumulative and preserved,'expiry_rejections':reject,
        'startup_evidence':[p.name for p in folder.glob('*_startup.json')],
        'downtime_excluded':True,'evidence_type':'真实运行 / 故障注入'})
    return observation

def run(round_number):
    if round_number not in (0,1,2):raise ValueError('At most two repairs; no stochastic gate retries')
    docs=ROOT/'specs/project2/v0.3.3'
    checked=subprocess.run([sys.executable,str(docs/'check_docs.py')],capture_output=True,text=True,encoding='utf-8')
    if checked.returncode:raise ValueError(checked.stdout)
    folder=ROOT/f'audit/project2-v1/ch13_v033_round{round_number}'
    if folder.exists():raise ValueError('Gate round already registered')
    folder.mkdir()
    (folder/'docs_check.log').write_text(checked.stdout,encoding='utf-8')
    authorization=read(ROOT/'audit/project2-v1/v033_authorization.json')
    if sha(ROOT/authorization['authorization_file'])!=authorization['sha256']:raise ValueError('Authority changed')
    save(folder/'plan.json',{'chapter':'Chap13','spec_version':'v0.3.3','repair_round':round_number,
       'checks':sorted(REQUIRED),'original_gate_script_sha256':sha(ROOT/'scripts/run_project2_ch13_gate.py'),
       'script_sha256':sha(Path(__file__)),'online_files':source_lock(ROOT),
       'policy_sha256':sha(docs/'recovery_accounting.json'),'spec_manifest_sha256':sha(docs/'version_manifest.json'),
       'authority_sha256':authorization['sha256'],'heldout_new_calls':0,
       'scenario_ids':['AC13-01','AC13-02','AC13-03','AC13-04','AC13-05','AC13-06'],
       'revised_predicate_only':'budget_not_reset: cumulative active time plus saved attempts and expiry rejection'})
    observation={};error=None
    try:
        with HostGuard(folder/'power'):observation=native(folder)
    except Exception as exc:
        logging.exception('Native gate failed');error={'category':type(exc).__name__,'detail':str(exc)[:400]}
    tests=['test_v033_budget_startup.py','test_v033_narrow_deadline.py','test_v033_dependency_timeout.py','test_runtime.py','test_runtime_v032.py','test_owned_cleanup.py','test_literal_components_v032.py','test_v03_contracts.py','test_v031_lineage.py']
    xml=folder/'runtime_contract.xml'
    with HostGuard(folder/'contract_power'):
        checked=subprocess.run([sys.executable,'-m','pytest',*[str(ROOT/'enterprise-ai-agent/tests/project2'/f) for f in tests],'-q','--junitxml='+str(xml)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    (folder/'runtime_contract.log').write_text(checked.stdout+'\n'+checked.stderr,encoding='utf-8')
    observation['runtime_contract_tests']=checked.returncode==0 and junit_pass(xml)
    baseline=read(ROOT/'evals/protocol_v0/baseline_v0.config.json')
    observation['frozen_budget_and_baseline']=all(sha(ROOT/n)==s for n,s in baseline['sut']['files'].items()) and sha(ROOT/'evals/project2-v1/calibration_v031/budget_frozen.json')==read(docs/'recovery_accounting.json')['old_budget_sha256']
    held=read(ROOT/'evals/project2-v1/ch12/heldout_receipt.json')
    observation['heldout_reuse_only']=held['heldout_stage_calls_project2']==1 and held['heldout_repetitions_project2']==3
    save(folder/'native_observations.json',{'observations':observation,'error':error})
    failed=[name for name in sorted(REQUIRED) if observation.get(name) is not True]
    result={'stage':'Chap13','status':'failed' if failed else 'passed','system_gate_executed':True,'gate_scope':'system_gate',
        'checks':[{'check':name,'expected':True,'observed':observation.get(name) is True,
          'status':'passed' if observation.get(name) is True else 'failed',
          'evidence_type':'契约测试(Mock)' if name=='runtime_contract_tests' else '故障注入' if name in {'real_subprocess_restart','real_sqlite_fault_located_by_trace','illegal_state_rejected','budget_not_reset'} else '真实运行',
          'evidence_file':(folder/'native_observations.json').relative_to(ROOT).as_posix()} for name in sorted(REQUIRED)],
        'failure_items':failed,'repair_rounds':round_number,'plan_sha256':sha(folder/'plan.json'),'native_error':error,
        's14_status':'未通过','heldout_new_calls':0,'budget_limits_changed':True,'budget_seconds':90,'attempts_cap':19,'llm_cap':6}
    assert stage_verdict(result)==result['status']
    save(folder/'gate.json',result);save(ROOT/'audit/project2-v1/v033_chap13_gate.json',result)
    logging.info('Chap13 v033 %s; failed=%s',result['status'],failed)
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--repair-round',type=int,required=True);args=ap.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    raise SystemExit(0 if run(args.repair_round)['status']=='passed' else 1)
