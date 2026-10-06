"""Create an explicit local Chap12 checkpoint; never push or open a PR."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
from pathlib import Path
from project2_close_stage import inspect_stage
from project2_v031_calibration import ROOT, digest, save


def selected_files(root: Path) -> list[str]:
    files=set()
    folders=['enterprise-ai-agent/agents/project2','enterprise-ai-agent/tests/project2','tests/project2',
             'specs/project2','audit/project2-v1','evals/project2-v1','evaluation_protocol']
    excluded={'node_modules','__pycache__','.pytest_cache','.git'}
    for name in folders:
        for directory,dirs,names in os.walk(root/name,followlinks=False):
            dirs[:]=[x for x in dirs if x not in excluded and not (Path(directory)/x).is_junction()]
            for filename in names:
                p=Path(directory)/filename
                if p.suffix not in {'.pyc','.pyo','.sqlite','.db'} and not p.is_symlink():files.add(p.relative_to(root).as_posix())
    files.update(['enterprise-ai-agent/api/project2_main.py','enterprise-ai-agent/models/project2.py',
                  'enterprise-ai-agent/tools/techqa_document_query.py','splits.json','splits.json.sha256','eval_protocol.md','.gitattributes'])
    scripts=['scripts/spec_preflight.py','scripts/run_project2_ch12_gate.py','scripts/run_project2_native_gate.py',
             'scripts/run_project2_v03_gate.py','scripts/run_project2_v031_gate.py','scripts/summarize_project2.py',
             'scripts/build_project2_v03.py','scripts/build_project2_v031.py','scripts/prepare_project2_v03_checker.py',
             'scripts/check_project2_v03_counts.py','scripts/keep_project2_measurement_awake.py',
             'scripts/keep_project2_measurement_awake.ps1','scripts/prepare_project2_quality_review.py',
             'scripts/project2_local_checkpoint.py']
    scripts.extend(x.relative_to(root).as_posix() for x in (root/'scripts').glob('project2*.py'))
    files.update(x for x in scripts if (root/x).is_file())
    state=root/'evals/protocol_v0'
    for name in ['baseline_v0.config.json','baseline_v0.quick.freeze.json','baseline_v0.source_snapshot.json',
                 'baseline_v0.source.zip','baseline_v0.evaluator_snapshot.json','baseline_v0.evaluator.zip',
                 'baseline_v0.index_artifacts.json','controls.json','tune.json','held-out.json',
                 'facts_tune.human_frozen.json','facts_held-out.human_frozen.json','heldout_ledger.jsonl',
                 'eval_protocol.v0.md','annotation_policy.a1.json']:
        p=state/name
        if p.is_file():files.add(p.relative_to(root).as_posix())
        side=p.with_suffix(p.suffix+'.sha256')
        if side.is_file():files.add(side.relative_to(root).as_posix())
    for partition in ('tune','held-out'):
        p=state/f'runs/baseline-v0-quick/{partition}/runs.json';files.add(p.relative_to(root).as_posix())
        files.add(p.with_suffix('.json.sha256').relative_to(root).as_posix())
        for name in ('summary.json','summary.json.sha256'):
            files.add((p.parent/name).relative_to(root).as_posix())
        summary=json.loads((root/f'evals/project2-v1/ch12/qa-{partition}/summary.json').read_text(encoding='utf-8'))
        for source in summary['required_facts']['annotation_sources']:
            files.add(source['path']);files.add(source['path']+'.sha256')
    transient={'audit/project2-v1/local_checkpoint_paths.nul','audit/project2-v1/local_checkpoint_manifest.json',
               'audit/project2-v1/v031_local_commit.log','audit/project2-v1/v031_checkpoint_prepare.log',
               'audit/project2-v1/local_checkpoint_index_report.json'}
    return sorted(x for x in files if (root/x).is_file() and x not in transient)


def checkpoint(root: Path, commit: bool) -> dict:
    execution=inspect_stage(root,'ch12')
    if not execution['execution_complete']:raise ValueError('Engineering gate and immutable evaluation records must complete first')
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=root,text=True).strip()
    if branch!='codex/project2-ch12':raise ValueError('Unexpected stage branch; do not switch or commit unrelated work')
    staged=subprocess.check_output(['git','diff','--cached','--name-only'],cwd=root,text=True).strip()
    if staged:raise ValueError('Preexisting staged files; preserve them, do not mix commits')
    files=selected_files(root)
    record={'stage':'Chap12','branch':branch,'files':{x:digest(root/x) for x in files},
            'bytes':sum((root/x).stat().st_size for x in files),
            'scope':'local checkpoint; engineering gate passed; S14 quality NOT accepted; no push/PR',
            'quality_acceptance':execution['quality']['acceptance']}
    audit=root/'audit/project2-v1';save(audit/'local_checkpoint_manifest.json',record)
    manifest='audit/project2-v1/local_checkpoint_manifest.json';files.append(manifest)
    pathspec=audit/'local_checkpoint_paths.nul';pathspec.write_bytes(('\0'.join(files)+'\0').encode('utf-8'))
    if not commit:return {'files':len(files),'bytes':record['bytes'],'prepared':True}
    subprocess.run(['git','add','--pathspec-from-file='+str(pathspec),'--pathspec-file-nul'],cwd=root,check=True)
    observed=set(subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=root).decode('utf-8').split('\0'))-{''}
    if not observed <= set(files):raise ValueError('Unexpected staged path; stop before commit')
    receipt=json.loads((root/'evals/project2-v1/ch12/heldout_receipt.json').read_text(encoding='utf-8'))
    message=f"Chap12: engineering gate PASS; S14 NOT ACCEPTED; held-out cumulative {receipt['heldout_stage_calls_project2']}/{receipt['heldout_repetitions_project2']}"
    subprocess.run(['git','commit','-m',message],cwd=root,check=True)
    # Git's CRLF normalization must not invalidate frozen byte hashes.
    import hashlib
    plan=json.loads((root/'evals/project2-v1/ch12/stage.plan.json').read_text(encoding='utf-8'))
    expected={**record['files'],**plan['online_files']}
    mismatches=[]
    for name,value in expected.items():
        content=subprocess.check_output(['git','show','HEAD:'+name],cwd=root)
        if hashlib.sha256(content).hexdigest()!=value:mismatches.append(name)
    save(audit/'local_checkpoint_index_report.json',{'status':'passed' if not mismatches else 'failed',
         'checked_files':len(expected),'mismatches':mismatches,'scope':'committed bytes vs evidence/source hashes; not answer quality'})
    if mismatches:raise ValueError('Committed byte hashes differ: '+str(mismatches))
    return {'files':len(observed),'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
            'message':message,'pushed':False}


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--commit',action='store_true');args=ap.parse_args()
    print(json.dumps(checkpoint(ROOT,args.commit),ensure_ascii=False,indent=2))
