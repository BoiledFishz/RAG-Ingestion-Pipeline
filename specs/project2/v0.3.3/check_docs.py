"""Exact authorized v033 delta; retain all earlier approved byte hashes and gates."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hashes(docs):return {p.name:sha(p) for p in sorted(docs.iterdir()) if p.is_file() and p.name not in {'approval_addendum.md','version_manifest.json'}}
def validate(docs,root,freezing=False):
    old=root/'specs/project2/v0.3.2'
    spec=importlib.util.spec_from_file_location('approved_v032_checker',old/'check_docs.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    results=m.validate(old,root)
    delta=json.loads((docs/'delta.json').read_text(encoding='utf-8'))
    assert delta['from_version']=='v0.3.2' and delta['to_version']=='v0.3.3'
    for name,digest in delta['protected_files'].items():
        if sha(root/name)!=digest:raise ValueError('Protected file changed: '+name)
    special={'spec.md','recovery_accounting.json','check_docs.py','delta.md','delta.json','approval_addendum.md','version_manifest.json'}
    assert {p.name for p in docs.iterdir() if p.is_file()} <= {p.name for p in old.iterdir() if p.is_file()},'Unexpected new spec file'
    for p in old.iterdir():
        if p.is_file() and p.name not in special and p.read_bytes()!=(docs/p.name).read_bytes():raise ValueError('Unapproved change: '+p.name)
    changes=delta['changes'];assert len(changes)==3
    c=changes[0];assert c['old']=='<a id="s09"></a>' and c['new'].startswith('### S08.4 v0.3.3')
    if (old/'spec.md').read_text(encoding='utf-8').replace(c['old'],c['new'])!=(docs/'spec.md').read_text(encoding='utf-8'):raise ValueError('Unapproved spec change')
    a=json.loads((old/'recovery_accounting.json').read_text(encoding='utf-8'));b=json.loads((docs/'recovery_accounting.json').read_text(encoding='utf-8'))
    for c in changes[1:]:
        assert c['file']=='recovery_accounting.json' and c['field'] in {'version','execution_limit_seconds'}
        assert a[c['field']]==c['old'];a[c['field']]=c['new']
    assert a==b and (b['dependency_limit'],b['llm_limit'],b['execution_limit_seconds'],b['run_lifetime_seconds'])==(19,6,90,900)
    assert b['execution_limit_seconds']==max(90,json.loads((root/b['old_budget_file']).read_text(encoding='utf-8'))['limits']['seconds'])
    assert sha(root/delta['diagnosis_file'])==delta['diagnosis_sha256']
    results+=['PASS v0.3.3: exact wall floor=max(90,37.941018)=90; startup/warmup before readiness',
        'PASS 19/6, S07/S14, all scenarios/queries/gates/CL and held-out rules unchanged',
        'PASS all old approved files byte-identical; read-only diagnosis frozen']
    if not freezing:
        manifest=json.loads((docs/'version_manifest.json').read_text(encoding='utf-8'))
        assert manifest['version']=='v0.3.3' and manifest['files']==hashes(docs)
        digest=sha(docs/'version_manifest.json');assert digest in (docs/'approval_addendum.md').read_text(encoding='utf-8')
        results+=['PASS v0.3.3 manifest SHA256='+digest]
    return results
def main():
    p=argparse.ArgumentParser();p.add_argument('--freeze-manifest',action='store_true');args=p.parse_args()
    docs=Path(__file__).resolve().parent;root=docs.parents[2]
    try:
        if args.freeze_manifest:
            if (docs/'version_manifest.json').exists():raise ValueError('Already frozen')
            validate(docs,root,True)
            (docs/'version_manifest.json').write_text(json.dumps({'version':'v0.3.3','authorization_date':'2026-10-06','files':hashes(docs),'excluded':['approval_addendum.md','version_manifest.json']},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            with (docs/'approval_addendum.md').open('a',encoding='utf-8') as f:f.write('\n版本 manifest SHA256：`'+sha(docs/'version_manifest.json')+'`\n')
        for line in validate(docs,root):print(line)
        return 0
    except (ValueError,AssertionError,KeyError,OSError) as exc:print('FAIL '+str(exc));return 1
if __name__=='__main__':raise SystemExit(main())
