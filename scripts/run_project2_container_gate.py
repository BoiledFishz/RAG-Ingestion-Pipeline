"""Chap14 real clean image/start/query/log/stop/restart gate; no held-out."""
from __future__ import annotations
import argparse
import hashlib
import json
import logging
import subprocess
import time
from datetime import datetime,timezone
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'audit/project2-course-completion-20261007'
DOCKER=r'C:/Program Files/Docker/Docker/resources/bin/docker.exe'
BASE='http://127.0.0.1:18012'
REQUIRED={'clean_build','ready_after_full_warmup','real_combined_completed','independent_count_exact',
          'input_fault_located_in_logs','stop_retains_volume','same_run_state_after_restart','owner_isolation'}
LOGGER=logging.getLogger(__name__)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def verdict(report):
    checks=report.get('checks',[])
    return 'passed' if {x['check'] for x in checks}==REQUIRED and len(checks)==len(REQUIRED) and all(x.get('observed') is True and x.get('expected') is True for x in checks) else 'failed'


def run(round_number:int):
    if round_number not in {0,1,2}:raise ValueError('At most two repairs')
    folder=AUDIT/f'container_gate_round{round_number}'
    folder.mkdir(exist_ok=False)
    checks=[];commands=[]
    def check(name,observed,kind,evidence):
        checks.append({'check':name,'expected':True,'observed':bool(observed),'status':'passed' if observed else 'failed',
                       'evidence_type':kind,'evidence_file':str(evidence.relative_to(ROOT))})
        LOGGER.info('Chap14 %s: %s',name,observed)
    def command(args,filename,timeout=60):
        result=subprocess.run([DOCKER,'--context','desktop-linux',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        path=folder/filename;path.write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
        commands.append({'command':args,'exit_code':result.returncode,'evidence_file':path.relative_to(ROOT).as_posix()})
        if result.returncode:raise RuntimeError('Docker step failed: '+filename)
        return result.stdout
    compose=['compose','-f','containers/project2/compose.yaml']
    def ready():
        started=time.monotonic();last=None
        while time.monotonic()-started<180:
            try:
                response=httpx.get(BASE+'/healthz',timeout=3)
                last=response.json()
                if response.status_code==200 and last.get('ready') is True:return last,time.monotonic()-started
            except (httpx.HTTPError,ValueError) as error:last=str(error)
            time.sleep(1)
        raise TimeoutError('Container startup not ready: '+str(last))
    source_paths=[ROOT/'containers/project2/Dockerfile',ROOT/'containers/project2/compose.yaml',
        ROOT/'enterprise-ai-agent/agents/project2/rag_process.py',ROOT/'enterprise-ai-agent/api/project2_main.py',
        ROOT/'enterprise-ai-agent/tools/techqa_document_query.py',ROOT/'specs/project2/v0.3.4/version_manifest.json',Path(__file__)]
    source_paths.extend(ROOT/name for name in ('enterprise-ai-agent/api/project2_container_main.py',
        'enterprise-ai-agent/agents/project2/container_cache.py','enterprise-ai-agent/agents/project2/container_transport.py'))
    save(folder/'plan.json',{'registered_at':datetime.now(timezone.utc).isoformat(),'required_checks':sorted(REQUIRED),
        'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in source_paths},
        'heldout_new_calls':0,'budget':{'attempts':19,'llm_calls':6,'seconds':90},'no_qa_oracle_to_worker':True})
    error=None;original=None
    try:
        image=json.loads(command(['image','inspect','techqa-project2-course:local'],'image.json'))[0]
        build=json.loads((AUDIT/f'container_build_receipt_gate{round_number}.json').read_text(encoding='utf-8'))
        buildlog=ROOT/build['build_log']
        materials=json.loads((AUDIT/'container_materials_manifest.json').read_text(encoding='utf-8'))
        intact=all(sha(ROOT/'.container-wheelhouse'/item['file'])==item['sha256'] for item in materials['wheels'])
        check('clean_build',intact and build['build_exit_code']==0 and build['sources_match'] and build['no_cache'] and build['network']=='none' and buildlog.exists() and 'ERROR' not in buildlog.read_text(encoding='utf-8') and image['Config']['Cmd'][-1]=='8000','真实运行',buildlog)
        command([*compose,'up','-d','--no-build','--pull','never'],'start.log')
        health,seconds=ready();save(folder/'ready.json',{'health':health,'elapsed_seconds':seconds})
        logs=command([*compose,'logs','--no-color','api'],'startup.log')
        startup=next((json.loads(line.split('P2_STARTUP ',1)[1]) for line in logs.splitlines() if 'P2_STARTUP ' in line),{})
        check('ready_after_full_warmup',startup.get('scope')=='full' and startup.get('warmup',{}).get('completed') is True and startup['warmup']['llm_calls']==0,'真实运行',folder/'startup.log')
        env_lines=(ROOT/'.container-secrets.env').read_text(encoding='utf-8').splitlines()
        credential=json.loads(next(line.split('=',1)[1] for line in env_lines if line.startswith('PROJECT2_CREDENTIALS_JSON=')))
        token=next(iter(credential));headers={'Authorization':'Bearer '+token}
        import csv
        scenarios=list(csv.DictReader((ROOT/'specs/project2/v0.3.4/acceptance_scenarios.csv').open(encoding='utf-8-sig',newline='')))
        request=json.loads(next(x['input_source_and_selection'] for x in scenarios if x['scenario_id']=='AC12-01'))
        sample=request.pop('sample_id');original_query=request['query']
        response=httpx.post(BASE+'/v2/project2/analysis',json=request,headers=headers,timeout=100)
        response.raise_for_status();original=response.json();save(folder/'combined_response.json',original)
        check('real_combined_completed',original['status']=='completed' and original['workers']['rag']['status']=='completed' and original['workers']['database']['status']=='completed' and bool(original['answer'].strip()) and bool(original['evidence']),'真实运行',folder/'combined_response.json')
        expected=json.loads((ROOT/'specs/project2/v0.3.4/data_expectations.json').read_text(encoding='utf-8'))['sample_measurements'][sample]
        check('independent_count_exact',[x['count'] for x in original['data_results']['groups']]==expected['counts'],'真实运行',folder/'combined_response.json')
        invalid=httpx.post(BASE+'/v2/project2/analysis',json={'query':original_query,'analysis_operation':'unsupported'},headers=headers,timeout=10)
        save(folder/'input_fault.json',{'http_status':invalid.status_code,'response':invalid.json()})
        logs=command([*compose,'logs','--no-color','api'],'diagnostic.log')
        trace=invalid.json()['trace_id']
        check('input_fault_located_in_logs',invalid.status_code==422 and 'P2_INVALID_INPUT trace_id='+trace in logs and invalid.json()['workers']['rag']['error']['category']=='invalid_input','故障注入',folder/'diagnostic.log')
        container=command([*compose,'ps','-q','api'],'container_id.log').strip()
        first=json.loads(command(['inspect',container],'before_stop.json'))[0]
        volume_names={m['Name'] for m in first['Mounts'] if m['Type']=='volume'}
        command([*compose,'stop','api'],'stop.log')
        volumes=json.loads(command(['volume','inspect',*sorted(volume_names)],'retained_volumes.json'))
        check('stop_retains_volume',{x['Name'] for x in volumes}==volume_names and bool(volume_names),'真实运行',folder/'retained_volumes.json')
        command([*compose,'start','api'],'restart.log');health,seconds=ready()
        save(folder/'restart_ready.json',{'health':health,'elapsed_seconds':seconds})
        stored=httpx.get(BASE+'/v2/project2/runs/'+original['run_id'],headers=headers,timeout=10)
        stored.raise_for_status();state=stored.json();save(folder/'restored_state.json',state)
        after=json.loads(command(['inspect',container],'after_restart.json'))[0]
        check('same_run_state_after_restart',state['run_id']==original['run_id'] and state['result']==original and after['State']['StartedAt']!=first['State']['StartedAt'] and {m['Name'] for m in after['Mounts'] if m['Type']=='volume'}==volume_names,'真实运行',folder/'restored_state.json')
        denied=httpx.get(BASE+'/v2/project2/runs/'+original['run_id'],timeout=10)
        save(folder/'owner_denied.json',{'http_status':denied.status_code,'response':denied.json()})
        check('owner_isolation',denied.status_code==403 and not denied.json().get('answer') and denied.json()['status']=='permission_denied','真实运行',folder/'owner_denied.json')
    except Exception as exc:
        error={'type':type(exc).__name__,'message':str(exc)};LOGGER.exception('Container gate failed')
        try:command([*compose,'logs','--no-color','api'],'failure.log')
        except Exception:pass
    finally:
        try:command([*compose,'stop','api'],'final_stop.log')
        except Exception:pass
    report={'stage':'Chap14','status':verdict({'checks':checks}),'system_gate_executed':True,'gate_scope':'system_gate',
        'checks':checks,'failure_items':sorted(REQUIRED-{x['check'] for x in checks if x['observed']}),
        'commands':commands,'error':error,'repair_rounds':round_number,'heldout_new_calls':0,
        'heldout_reuse':'Chap13 stage2 records; container transport/platform only, frozen generator/model/prompt unchanged',
        'source_plan_sha256':sha(folder/'plan.json'),'s14_status':'未通过','volumes_deleted':False}
    save(folder/'gate.json',report)
    LOGGER.info('Chap14 gate=%s %s/%s',report['status'],sum(x['observed'] for x in checks),len(REQUIRED))
    return int(report['status']!='passed')


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    parser=argparse.ArgumentParser();parser.add_argument('--round',type=int,default=0)
    raise SystemExit(run(parser.parse_args().round))
