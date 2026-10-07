"""Verify the authorized recovery-only delta; prior approved versions are immutable."""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def hashes(docs: Path) -> dict:
    return {p.name:sha(p) for p in sorted(docs.iterdir()) if p.is_file()
            and p.name not in {'approval_addendum.md','version_manifest.json'}}

def validate(docs: Path, root: Path, freezing: bool=False) -> list[str]:
    old=root/'specs/project2/v0.3.1'
    loader=importlib.util.spec_from_file_location('approved_v031_checker',old/'check_docs.py')
    module=importlib.util.module_from_spec(loader);loader.loader.exec_module(module)
    results=module.validate(old,root)
    delta=json.loads((docs/'delta.json').read_text(encoding='utf-8'))
    assert delta['from_version']=='v0.3.1' and delta['to_version']=='v0.3.2'
    for name,digest in delta['protected_files'].items():
        if sha(root/name)!=digest:raise ValueError('Protected old file changed: '+name)
    special={'spec.md','acceptance_scenarios.csv','check_docs.py','delta.md','delta.json',
             'approval_addendum.md','version_manifest.json'}
    for p in old.iterdir():
        if p.is_file() and p.name not in special and p.read_bytes()!=(docs/p.name).read_bytes():
            raise ValueError('Unapproved file change: '+p.name)
    changes=delta['changes']
    if len(changes)!=4 or changes[0]['file']!='spec.md':raise ValueError('Unexpected delta')
    insertion=changes[0]
    if insertion['old']!='<a id="s09"></a>' or not insertion['new'].startswith('### S08.3 v0.3.2'):
        raise ValueError('Unexpected insertion')
    if (old/'spec.md').read_text(encoding='utf-8').replace(insertion['old'],insertion['new'])!=(docs/'spec.md').read_text(encoding='utf-8'):
        raise ValueError('Unapproved design, S07, S14 or budget change')
    rows=lambda p:list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
    before=rows(old/'acceptance_scenarios.csv');after=rows(docs/'acceptance_scenarios.csv')
    expected={('AC13-01','setup'),('AC13-02','setup'),('AC13-02','assertions')}
    if {(x['scenario_id'],x['column']) for x in changes[1:]}!=expected:raise ValueError('Scenario delta outside authorization')
    for change in changes[1:]:
        row=next(x for x in before if x['scenario_id']==change['scenario_id'])
        if row[change['column']]!=change['old']:raise ValueError('Old assertion differs')
        row[change['column']]=change['new']
    if before!=after:raise ValueError('Unapproved scenario, query, gate, status or evidence change')
    policy=json.loads((docs/'recovery_accounting.json').read_text(encoding='utf-8'))
    frozen=json.loads((root/policy['old_budget_file']).read_text(encoding='utf-8'))
    if sha(root/policy['old_budget_file'])!=policy['old_budget_sha256']:raise ValueError('Frozen budget changed')
    if (policy['dependency_limit'],policy['llm_limit'],policy['execution_limit_seconds'])!=(19,6,frozen['limits']['seconds']):
        raise ValueError('Numeric limits changed')
    if policy['run_lifetime_seconds']!=900 or policy['heartbeat_seconds']!=.25:raise ValueError('Undeclared accounting policy')
    if policy['state_retention_seconds']!=86400 or policy['trace_retention_seconds']!=604800:raise ValueError('CL retention changed')
    results.append('PASS v0.3.2 scope: recovery accounting only; 19/6/37.941018 unchanged; lifetime=900s')
    results.append('PASS scenarios/queries/matrix/gates/status/evidence unchanged outside 3 authorized cells')
    if not freezing:
        manifest=json.loads((docs/'version_manifest.json').read_text(encoding='utf-8'))
        if manifest['version']!='v0.3.2' or manifest['files']!=hashes(docs):raise ValueError('Frozen v0.3.2 manifest differs')
        digest=sha(docs/'version_manifest.json')
        if digest not in (docs/'approval_addendum.md').read_text(encoding='utf-8'):raise ValueError('Missing approval manifest hash')
        results.append('PASS v0.3.2 manifest SHA256='+digest)
    return results

def main() -> int:
    parser=argparse.ArgumentParser();parser.add_argument('--freeze-manifest',action='store_true');args=parser.parse_args()
    docs=Path(__file__).resolve().parent;root=docs.parents[2]
    try:
        if args.freeze_manifest:
            if (docs/'version_manifest.json').exists():raise ValueError('Already frozen')
            validate(docs,root,True)
            (docs/'version_manifest.json').write_text(json.dumps({'version':'v0.3.2','authorization_date':'2026-10-06',
                'files':hashes(docs),'excluded':['approval_addendum.md','version_manifest.json']},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            with (docs/'approval_addendum.md').open('a',encoding='utf-8') as stream:
                stream.write('\n版本 manifest SHA256：`'+sha(docs/'version_manifest.json')+'`\n')
        for line in validate(docs,root):print(line)
        return 0
    except (ValueError,AssertionError,KeyError,OSError) as error:
        print('FAIL '+str(error));return 1

if __name__=='__main__':raise SystemExit(main())
