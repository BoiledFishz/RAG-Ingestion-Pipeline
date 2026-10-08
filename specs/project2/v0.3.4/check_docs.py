"""Validate only the authorized literal-component/data supplement."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def hashes(docs):
    return {p.name:sha(p) for p in sorted(docs.iterdir()) if p.is_file()
            and p.name not in {'approval_addendum.md','version_manifest.json'}}

def validate(docs,root,freezing=False):
    old=root/'specs/project2/v0.3.3'
    loader=importlib.util.spec_from_file_location('approved_v033_checker',old/'check_docs.py')
    module=importlib.util.module_from_spec(loader);loader.loader.exec_module(module)
    results=module.validate(old,root)
    delta=read(docs/'delta.json')
    assert (delta['from_version'],delta['to_version'])==('v0.3.3','v0.3.4')
    for name,expected in delta['protected_files'].items():
        if sha(root/name)!=expected:raise ValueError('Protected approved file changed: '+name)
    special={'spec.md','check_docs.py','delta.json','delta.md','approval_addendum.md','version_manifest.json'}
    expected_files={p.name for p in old.iterdir() if p.is_file()}|{'data_expectations.json'}
    if freezing:expected_files.remove('version_manifest.json')
    assert {p.name for p in docs.iterdir() if p.is_file()}==expected_files,'Unexpected specification file'
    for p in old.iterdir():
        if p.is_file() and p.name not in special and p.read_bytes()!=(docs/p.name).read_bytes():
            raise ValueError('Unapproved copied file change: '+p.name)
    changes=delta['changes'];assert len(changes)==2
    c=changes[0];assert c['file']=='spec.md' and c['old']=='<a id="s02"></a>'
    assert c['new'].startswith('### S01.2 v0.3.4')
    assert (old/'spec.md').read_text(encoding='utf-8').replace(c['old'],c['new'])==(docs/'spec.md').read_text(encoding='utf-8'),'Out-of-scope spec edit'
    sidecar=read(docs/'data_expectations.json')
    assert sha(root/sidecar['source_file'])==sidecar['source_sha256']
    assert sha(root/sidecar['independent_proof'])==sidecar['independent_proof_sha256']==changes[1]['proof_sha256']
    proof=read(root/sidecar['independent_proof'])
    assert proof['worker_or_catalogue_code_reused'] is False and proof['official_qa_fields_used']==[]
    assert proof['llm_calls']==proof['heldout_calls']==0 and proof['proposal_version']==2
    expected=json.loads(json.dumps(read(root/sidecar['source_file'])['sample_measurements']))
    assert changes[1]['sample_keys']==[x['sample_id'] for x in proof['differences']]
    assert len(proof['differences'])==1
    for item in proof['differences']:
        assert expected[item['sample_id']]==item['frozen_expectation']
        a,b=item['independent_counts'];overlap=item['intersection']
        expected[item['sample_id']]={'predicates':item['independent_literal_predicates'],'counts':[a,b],
            'intersection':overlap,'delta_a_minus_b':a-b,'union':a+b-overlap,
            'measurement_complete':True,'not_worker_execution':True}
    assert expected==sidecar['sample_measurements'],'Unapproved data expectation change'
    assert sidecar['official_fields_modified'] is False and sidecar['historical_results_regraded'] is False
    results+=['PASS v0.3.4: independent full-corpus data expectation bound to approved v2 evidence',
        'PASS old approved files unchanged; 50 tasks, all scenarios, S07/S14, 19/6/90, CL and held-out unchanged']
    if not freezing:
        manifest=read(docs/'version_manifest.json')
        assert manifest['version']=='v0.3.4' and manifest['files']==hashes(docs)
        digest=sha(docs/'version_manifest.json');assert digest in (docs/'approval_addendum.md').read_text(encoding='utf-8')
        results+=['PASS v0.3.4 manifest SHA256='+digest]
    return results

def main():
    p=argparse.ArgumentParser();p.add_argument('--freeze-manifest',action='store_true');args=p.parse_args()
    docs=Path(__file__).resolve().parent;root=docs.parents[2]
    try:
        if args.freeze_manifest:
            if (docs/'version_manifest.json').exists():raise ValueError('Already frozen')
            validate(docs,root,True)
            (docs/'version_manifest.json').write_text(json.dumps({'version':'v0.3.4','authorization_date':'2026-10-07',
                'files':hashes(docs),'excluded':['approval_addendum.md','version_manifest.json']},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            with (docs/'approval_addendum.md').open('a',encoding='utf-8') as f:f.write('\n版本 manifest SHA256：`'+sha(docs/'version_manifest.json')+'`\n')
        for line in validate(docs,root):print(line)
        return 0
    except (ValueError,AssertionError,KeyError,OSError) as exc:print('FAIL '+str(exc));return 1
if __name__=='__main__':raise SystemExit(main())
