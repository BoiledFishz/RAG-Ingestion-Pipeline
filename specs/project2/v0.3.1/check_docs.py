"""Keep the prior structural checks; permit only one exact operational insertion."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_scope(docs: Path, root: Path) -> list[str]:
    delta=json.loads((docs/'delta.json').read_text(encoding='utf-8'))
    if delta['from_version']!='v0.3' or delta['to_version']!='v0.3.1': raise ValueError('Invalid revision')
    for name,digest in delta['protected_files'].items():
        if sha(root/name)!=digest: raise ValueError('Protected old version changed: '+name)
    for name,digest in delta['batch1_files'].items():
        if sha(root/name)!=digest: raise ValueError('Batch 1 changed: '+name)
    old=root/'specs/project2/v0.3'
    special={'spec.md','check_docs.py','delta.md','delta.json','approval_addendum.md','version_manifest.json'}
    for path in old.iterdir():
        if path.is_file() and path.name not in special and (docs/path.name).read_bytes()!=path.read_bytes():
            raise ValueError('Unapproved field/file change: '+path.name)
    value=(old/'spec.md').read_text(encoding='utf-8')
    changes=delta['changes']
    if len(changes)!=1 or changes[0]['file']!='spec.md' or changes[0]['old']!='<a id="s09"></a>':
        raise ValueError('Only one S08.2 insertion is authorized')
    addition=changes[0]['new'].removesuffix(changes[0]['old'])
    if not addition.startswith('### S08.2 v0.3.1') or not changes[0]['new'].endswith(changes[0]['old']):
        raise ValueError('Invalid insertion')
    if value.replace(changes[0]['old'],changes[0]['new'])!=(docs/'spec.md').read_text(encoding='utf-8'):
        raise ValueError('Protected S08.1/matrix/design text changed')
    p=json.loads((docs/'operation_protocol.json').read_text(encoding='utf-8'))
    prior=json.loads((root/'evals/project2-v1/calibration_v03/protocol.json').read_text(encoding='utf-8'))
    allowed={'version','operational_rules','original_protocol_sha256','batch1_files','protected_files'}
    if {k:v for k,v in p.items() if k not in allowed}!={k:v for k,v in prior.items() if k not in allowed}:
        raise ValueError('Sampling, slots, formula, fuse or frozen rule changed')
    rules=p['operational_rules']
    expected={'batch_numbers':[2,3],'heartbeat_seconds':5,'suspended_gap_seconds':30,
        'sleep_prevention_flags':0x80000001,'reset_flags':0x80000000,
        'selection':'first complete uncensored non-suspended batch only; no across-batch mixing',
        'retry':'batch 3 only after host_suspended batch 2; non-sleep censor stops',
        'cap_floor_enabled':True,'signed_cap_floor':{'attempts':16,'llm_calls':6},
        'wall_clock_floor':False,'psutil_unplugged_stops':True,'install_dependencies':False}
    if rules!=expected: raise ValueError('Operational rules differ from preregistered authorization')
    protocol=root/'evals/project2-v1/calibration_v031/protocol.json'
    if (docs/'operation_protocol.json').read_bytes()!=protocol.read_bytes() or sha(protocol)!=delta['protocol_sha256']:
        raise ValueError('Operational protocol hash mismatch')
    if sha(protocol) not in addition: raise ValueError('Protocol hash absent from added specification')
    return ['PASS v0.3.1仅S08.2操作性插入；旧三版/批次1逐文件不变；S08.1/S07/42场景/门禁/CL决定保持',
            'PASS 同一300槽位；进程内防睡眠/5秒心跳/>30秒整批无效；首个完整批次单独决策；16/6下限已登记']


def artifact_hashes(docs: Path) -> dict:
    return {f.name:sha(f) for f in sorted(docs.iterdir()) if f.is_file() and f.name not in {'version_manifest.json','approval_addendum.md'}}


def validate(docs: Path, root: Path, freezing: bool=False) -> list[str]:
    path=root/'specs/project2/v0.3/check_docs.py'
    spec=importlib.util.spec_from_file_location('frozen_v03_checker',path)
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    old.validate(root/'specs/project2/v0.3',root)
    scope=validate_scope(docs,root)
    old.validate_revision_scope=lambda d,r:scope
    result=old.validate(docs,root,freezing=True)
    if not freezing:
        m=json.loads((docs/'version_manifest.json').read_text(encoding='utf-8'))
        if m['version']!='v0.3.1' or m['files']!=artifact_hashes(docs): raise ValueError('v0.3.1 manifest differs')
        digest=sha(docs/'version_manifest.json')
        if digest not in (docs/'approval_addendum.md').read_text(encoding='utf-8'): raise ValueError('Manifest hash absent from addendum')
        result.append('PASS v0.3.1 manifest SHA256='+digest)
    return result


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--docs-dir',type=Path,default=Path(__file__).resolve().parent)
    ap.add_argument('--project-root',type=Path,default=Path(__file__).resolve().parents[3])
    ap.add_argument('--freeze-manifest',action='store_true');args=ap.parse_args()
    try:
        docs=args.docs_dir.resolve();root=args.project_root.resolve()
        if args.freeze_manifest:
            if (docs/'version_manifest.json').exists(): raise ValueError('Manifest already frozen')
            validate(docs,root,True)
            m={'version':'v0.3.1','authorization_date':'2026-10-05','files':artifact_hashes(docs),
               'excluded':['version_manifest.json','approval_addendum.md'],'exclusion_reason':'avoid circular hash; addendum quotes manifest'}
            (docs/'version_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            path=docs/'approval_addendum.md';text=path.read_text(encoding='utf-8')
            if text.count('版本 manifest SHA256：待生成')!=1: raise ValueError('Approval hash placeholder not unique')
            path.write_text(text.replace('版本 manifest SHA256：待生成','版本 manifest SHA256：`'+sha(docs/'version_manifest.json')+'`'),encoding='utf-8')
        sys.stdout.write('\n'.join(validate(docs,root))+'\n');return 0
    except (ValueError,KeyError,OSError,TypeError) as exc:
        sys.stdout.write('FAIL '+str(exc)+'\n');return 1


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
