"""Validate the selected whole batch before admitting its hard budget."""
import hashlib
import json
from pathlib import Path


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_bundle(folder: Path) -> dict:
    path=folder/'frozen_manifest.json'
    if not path.is_file(): raise ValueError('Whole calibration bundle is not frozen')
    data=json.loads(path.read_text(encoding='utf-8'))
    for name,digest in data['files'].items():
        target=folder/name
        if not target.resolve().is_relative_to(folder.resolve()) or sha(target)!=digest:
            raise ValueError('Frozen calibration evidence changed: '+name)
    return data


def selected_evidence(root: Path) -> tuple[dict,Path]:
    folder=root/'evals/project2-v1/calibration_v031'
    if not (folder/'decision.json').exists(): raise ValueError('No whole-batch decision; activation prohibited')
    outer=frozen_bundle(folder)
    if set(outer['files'])!={'protocol.json','batches.json','decision.json'}: raise ValueError('Incomplete batch decision bundle')
    decision=json.loads((folder/'decision.json').read_text(encoding='utf-8'))
    number=decision.get('selected_batch')
    if decision.get('status')!='selected' or number not in (2,3) or decision.get('mixing_batches') is not False or decision.get('excluded_individual_records')!=0:
        raise ValueError('Decision must use a new complete unmixed batch')
    ledger=json.loads((folder/'batches.json').read_text(encoding='utf-8'))['batches']
    accepted=[x['batch'] for x in ledger if x['used_for_decision']]
    if accepted!=[number] or any(x['batch']<number and x['status']=='selected' for x in ledger):
        raise ValueError('First complete batch selection differs')
    if number==3 and not any(x['batch']==2 and x['status']=='host_suspended' for x in ledger):
        raise ValueError('Batch 3 requires recorded host-suspended batch 2')
    target=folder/f'batch{number}';bundle=frozen_bundle(target)
    required={'protocol.json','requests.jsonl','summary.json','heartbeats.jsonl','host_guard.json','host_guard_active.json'}
    if set(bundle['files'])!=required or sha(target/'frozen_manifest.json')!=decision['batch_manifest_sha256']:
        raise ValueError('Selected batch evidence incomplete')
    summary=json.loads((target/'summary.json').read_text(encoding='utf-8'))
    if summary['status']!='selected' or summary['requests']!=300 or summary['expected']!=300 or summary['host_suspended'] or summary.get('failure'):
        raise ValueError('Selected batch incomplete, suspended or censored')
    guard=json.loads((target/'host_guard.json').read_text(encoding='utf-8'))
    beats=[json.loads(x) for x in (target/'heartbeats.jsonl').read_text(encoding='utf-8').splitlines()]
    if guard['status']!='released' or guard['host_suspended'] or guard['failure'] or not beats or any(x['host_suspended'] or (x['gap_seconds'] or 0)>30 for x in beats):
        raise ValueError('Host monitoring failed')
    protocol=json.loads((folder/'protocol.json').read_text(encoding='utf-8'))
    if sha(folder/'protocol.json')!=decision['protocol_sha256'] or (target/'protocol.json').read_bytes()!=(folder/'protocol.json').read_bytes():
        raise ValueError('Protocol mismatch')
    for name,digest in {**protocol['protected_files'],**protocol['batch1_files']}.items():
        if sha(root/name)!=digest: raise ValueError('Preserved original changed: '+name)
    if sha(root/'specs/project2/v0.3.1/version_manifest.json')!=decision['spec_manifest_sha256']:
        raise ValueError('Authorized operational specification changed')
    docs=root/'specs/project2/v0.3.1'
    authorized=json.loads((docs/'version_manifest.json').read_text(encoding='utf-8'))
    if any(sha(docs/name)!=digest for name,digest in authorized['files'].items()):
        raise ValueError('Approved operational document changed')
    if decision['limits']!=summary['limits']: raise ValueError('Budget differs from selected batch')
    return decision,target


def read_v031(root: Path) -> dict | None:
    folder=root/'evals/project2-v1/calibration_v031';path=folder/'budget_frozen.json'
    if not path.is_file():return None
    try:
        profile=json.loads(path.read_text(encoding='utf-8'))
        if profile['status']!='frozen' or profile['version']!='project2-v0.3.1-budget-v1': raise ValueError('Unverified budget profile')
        decision,target=selected_evidence(root)
        if profile['limits']!=decision['limits'] or profile['decision_manifest_sha256']!=sha(folder/'frozen_manifest.json') or profile['selected_batch']!=decision['selected_batch']:
            raise ValueError('Profile differs from frozen first complete batch')
        limits=profile['limits']
        if not (isinstance(limits['attempts'],int) and 16<=limits['attempts']<=40 and isinstance(limits['llm_calls'],int)
                and 6<=limits['llm_calls']<=15 and isinstance(limits['seconds'],(int,float)) and 0<limits['seconds']<=450):
            raise ValueError('Budget outside authorized formula envelope')
        return limits
    except (KeyError,OSError,TypeError) as exc: raise ValueError('Incomplete verified Project2 budget evidence') from exc
