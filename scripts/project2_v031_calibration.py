"""Sleep-protected whole batches. Never mix, filter or overwrite batch 1."""
from __future__ import annotations
import argparse
import asyncio
import copy
import ctypes
import importlib.util
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from project2_v03_calibration import digest, measure, save, select_limits, verify

ROOT=Path(__file__).resolve().parents[1]
LOGGER=logging.getLogger(__name__)
FOLDER='evals/project2-v1/calibration_v031'


class HostSuspended(RuntimeError): pass
class Unplugged(RuntimeError): pass


def heartbeat_gap(previous: float, current: float) -> bool:
    return current-previous>30


def execution_state(flags: int) -> int:
    if os.name!='nt': raise RuntimeError('Windows host required; no system configuration fallback')
    call=ctypes.WinDLL('kernel32',use_last_error=True).SetThreadExecutionState
    call.argtypes=[ctypes.c_uint];call.restype=ctypes.c_uint
    result=int(call(flags))
    if not result: raise OSError(ctypes.get_last_error(),'SetThreadExecutionState failed')
    return result


def battery_check() -> bool | None:
    if importlib.util.find_spec('psutil') is None: return None
    import psutil
    value=psutil.sensors_battery()
    return None if value is None else bool(value.power_plugged)


class HostGuard:
    def __init__(self, folder: Path, *, execution_state: Callable[[int],int]=execution_state,
                 battery_check: Callable[[],bool | None]=battery_check, heartbeat_seconds: float=5):
        self.folder=folder;self.execution_state=execution_state;self.battery_check=battery_check
        self.heartbeat_seconds=heartbeat_seconds;self.stop=threading.Event();self.lock=threading.Lock()
        self.previous=None;self.host_suspended=False;self.gaps=[];self.failure=None
        self.thread=None;self.active=False;self.battery=None;self.calls=[]

    def beat(self) -> None:
        with self.lock:
            now=time.time();gap=None if self.previous is None else now-self.previous
            row={'wall_time':now,'utc':datetime.now(timezone.utc).isoformat(),'gap_seconds':gap,
                 'host_suspended':gap is not None and heartbeat_gap(self.previous,now)}
            if row['host_suspended']:
                self.host_suspended=True;self.gaps.append(row)
            with (self.folder/'heartbeats.jsonl').open('a',encoding='utf-8') as f:
                f.write(json.dumps(row)+'\n');f.flush()
            self.previous=now

    def heartbeat_loop(self) -> None:
        while not self.stop.wait(self.heartbeat_seconds):
            try:
                self.beat()
                if self.battery_check() is False: self.failure='unplugged'
            except Exception as exc:
                self.failure='heartbeat_failure: '+str(exc)
                return

    def ensure_running(self) -> None:
        self.beat()
        if self.host_suspended: raise HostSuspended('wall heartbeat gap >30 seconds')
        if self.failure=='unplugged': raise Unplugged('AC disconnected during batch')
        if self.failure: raise RuntimeError(self.failure)

    def __enter__(self):
        self.folder.mkdir(parents=True,exist_ok=True)
        self.battery=self.battery_check()
        if self.battery is False: raise Unplugged('psutil reports not plugged in; no requests started')
        previous=self.execution_state(0x80000001);self.calls.append({'flags':0x80000001,'previous':previous})
        self.active=True
        try:
            self.beat();self.thread=threading.Thread(target=self.heartbeat_loop,name='project2-wall-heartbeat',daemon=True)
            self.thread.start()
        except BaseException:
            self.execution_state(0x80000000);self.active=False;raise
        save(self.folder/'host_guard_active.json',{'status':'active','process_id':os.getpid(),
             'flags':0x80000001,'scope':'calling runner thread only; no system power policy changes',
             'psutil_installed':importlib.util.find_spec('psutil') is not None,'power_plugged':self.battery})
        return self

    def __exit__(self, *unused):
        self.stop.set()
        if self.thread: self.thread.join(timeout=6)
        try:
            self.beat()
        finally:
            if self.active:
                previous=self.execution_state(0x80000000);self.calls.append({'flags':0x80000000,'previous':previous})
                self.active=False
            save(self.folder/'host_guard.json',{'status':'host_suspended' if self.host_suspended else 'released',
                 'host_suspended':self.host_suspended,'gaps':self.gaps,'failure':self.failure,
                 'power_plugged':self.battery,'psutil_installed':importlib.util.find_spec('psutil') is not None,
                 'calls':self.calls,'process_id':os.getpid(),'system_power_settings_changed':False})


def slots(protocol: dict) -> set[tuple[str,str,int]]:
    return {(path,sample['sample_id'],repeat) for path in protocol['paths']
            for sample in protocol['samples'] for repeat in range(1,protocol['repeats']+1)}


def registration(root: Path) -> dict:
    source=root/'evals/project2-v1/calibration_v03/protocol.json'
    old=json.loads(source.read_text(encoding='utf-8'))
    value=copy.deepcopy(old);value['version']='project2-v0.3.1-whole-batches-v1'
    value['original_protocol_sha256']=digest(source)
    value['batch1_files']={f.relative_to(root).as_posix():digest(f)
          for f in (root/'evals/project2-v1/calibration_v03').iterdir() if f.is_file()}
    value['protected_files'].update({f.relative_to(root).as_posix():digest(f)
          for f in (root/'specs/project2/v0.3').iterdir() if f.is_file()})
    value['operational_rules']={'batch_numbers':[2,3],'heartbeat_seconds':5,'suspended_gap_seconds':30,
          'sleep_prevention_flags':0x80000001,'reset_flags':0x80000000,
          'selection':'first complete uncensored non-suspended batch only; no across-batch mixing',
          'retry':'batch 3 only after host_suspended batch 2; non-sleep censor stops',
          'cap_floor_enabled':True,'signed_cap_floor':{'attempts':16,'llm_calls':6},
          'wall_clock_floor':False,'psutil_unplugged_stops':True,'install_dependencies':False}
    return value


def decide_batch(rows: list[dict], host_suspended: bool, protocol: dict | None=None) -> dict:
    if host_suspended: return {'status':'host_suspended','limits':None,'reason':'wall heartbeat gap >30 seconds'}
    if protocol is None: return {'status':'incomplete','limits':None}
    observed=[(x['path'],x['sample_id'],x['repeat']) for x in rows]
    if len(observed)!=300 or len(set(observed))!=300 or set(observed)!=slots(protocol):
        return {'status':'incomplete','limits':None,'reason':'incomplete or duplicate registered slots'}
    paths={path:select_limits([x for x in rows if x['path']==path]) for path in protocol['paths']}
    status='selected' if all(x['status']=='selected' for x in paths.values()) else 'stopped_structural_fuse' if any(x['status']=='stopped_structural_fuse' for x in paths.values()) else 'incomplete_censored'
    limits=None
    if status=='selected':
        limits={key:max(x['limits'][key] for x in paths.values()) for key in ('attempts','llm_calls','seconds')}
        if protocol['operational_rules']['cap_floor_enabled']:
            for key,value in protocol['operational_rules']['signed_cap_floor'].items(): limits[key]=max(value,limits[key])
    return {'status':status,'limits':limits,'paths':paths,'requests':len(rows),'expected':300,
            'host_suspended':False,'reason':'non-sleep envelope censor' if status=='incomplete_censored' else None}


def next_batch(report: dict, number: int) -> int | None:
    return 3 if number==2 and report['status']=='host_suspended' else None


def freeze(folder: Path, names: list[str]) -> None:
    if (folder/'frozen_manifest.json').exists(): raise ValueError('Batch already frozen; refusing rewrite')
    save(folder/'frozen_manifest.json',{'files':{name:digest(folder/name) for name in names if (folder/name).is_file()}})


def run(root: Path) -> int:
    folder=root/FOLDER;protocol=json.loads((folder/'protocol.json').read_text(encoding='utf-8'))
    verify(root,protocol)
    for name,sha in protocol['batch1_files'].items():
        if digest(root/name)!=sha: raise ValueError('Batch 1 changed: '+name)
    docs=root/'specs/project2/v0.3.1'
    manifest=json.loads((docs/'version_manifest.json').read_text(encoding='utf-8'))
    for name,sha in manifest['files'].items():
        if digest(docs/name)!=sha: raise ValueError('v0.3.1 changed: '+name)
    if (folder/'decision.json').exists(): raise ValueError('Decision already frozen; no new automatic batch')
    ledger=[{'batch':1,'status':'incomplete_censored','censor_reason':'host sleep; P2-PLATFORM-01/combination/repeat3',
             'used_for_decision':False,'label':'批次 1：因主机睡眠删失，未用于决策',
             'path':'evals/project2-v1/calibration_v03','requests':300}]
    number=2
    while number:
        target=folder/f'batch{number}'
        if target.exists(): raise ValueError('Batch directory exists; refusing overwrite or resume a selected subset')
        target.mkdir();save(target/'protocol.json',protocol)
        guard=HostGuard(target);failure=None
        try:
            with guard:
                asyncio.run(measure(root,protocol,resume=False,output_dir=target,guard=guard,freeze_output=False))
        except Exception as exc:
            failure={'category':type(exc).__name__,'detail':str(exc)[:400]}
            LOGGER.exception('Whole batch interrupted')
        raw=target/'requests.jsonl'
        rows=[json.loads(x) for x in raw.read_text(encoding='utf-8').splitlines()] if raw.exists() else []
        summary=decide_batch(rows,guard.host_suspended,protocol)
        if failure and not guard.host_suspended:
            summary={'status':'unplugged' if isinstance(failure,dict) and failure['category']=='Unplugged' else 'runner_failed',
                     'limits':None,'requests':len(rows),'expected':300,'failure':failure}
        summary.update({'batch':number,'heldout_calls':0,'protocol_sha256':digest(folder/'protocol.json'),
             'raw_sha256':digest(raw) if raw.exists() else None,'host_suspended':guard.host_suspended,
             'failure':failure,'production_limits_changed':False,'spec_manifest_sha256':digest(docs/'version_manifest.json')})
        save(target/'summary.json',summary)
        freeze(target,['protocol.json','requests.jsonl','summary.json','heartbeats.jsonl','host_guard.json','host_guard_active.json'])
        ledger.append({'batch':number,'status':summary['status'],'censor_reason':summary.get('reason') or summary.get('failure'),
             'used_for_decision':summary['status']=='selected','path':target.relative_to(root).as_posix(),'requests':len(rows)})
        save(folder/'batches.json',{'batches':ledger,'heldout_calls':0})
        LOGGER.info('batch=%d result=%s requests=%d',number,summary['status'],len(rows))
        if summary['status']=='selected':
            save(folder/'decision.json',{'status':'selected','selected_batch':number,'limits':summary['limits'],
                  'batch_manifest_sha256':digest(target/'frozen_manifest.json'),'protocol_sha256':digest(folder/'protocol.json'),
                  'spec_manifest_sha256':digest(docs/'version_manifest.json'),'heldout_calls':0,
                  'mixing_batches':False,'excluded_individual_records':0})
        number=next_batch(summary,number)
    if not (folder/'decision.json').exists():
        save(folder/'decision.json',{'status':ledger[-1]['status'],'selected_batch':None,'limits':None,
                                  'heldout_calls':0,'mixing_batches':False,'excluded_individual_records':0})
    freeze(folder,['protocol.json','batches.json','decision.json'])
    return 0 if ledger[-1]['used_for_decision'] else 1


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--register',action='store_true');parser.add_argument('--measure',action='store_true')
    args=parser.parse_args();folder=ROOT/FOLDER
    if args.register:
        value=registration(ROOT);path=folder/'protocol.json'
        if path.exists() and json.loads(path.read_text(encoding='utf-8'))!=value: raise ValueError('Registration differs; refusing overwrite')
        if not path.exists(): save(path,value)
        LOGGER.info('preregistered SHA256=%s; signed floor=16/6; 300 identical slots',digest(path))
    return run(ROOT) if args.measure else 0


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    raise SystemExit(main())
