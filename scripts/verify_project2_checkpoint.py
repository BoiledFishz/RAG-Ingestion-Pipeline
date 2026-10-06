"""Read Git blobs directly to verify frozen bytes; no checkout or evaluation."""
from __future__ import annotations
import hashlib
import json
import subprocess
from pathlib import Path
from project2_v031_calibration import ROOT, digest, save


def verify(root: Path) -> dict:
    audit=root/'audit/project2-v1'
    record=json.loads((audit/'local_checkpoint_manifest.json').read_text(encoding='utf-8'))
    plan=json.loads((root/'evals/project2-v1/ch12/stage.plan.json').read_text(encoding='utf-8'))
    expected={**record['files'],**plan['online_files']}
    prior_attributes=expected['.gitattributes'];expected['.gitattributes']=digest(root/'.gitattributes')
    mismatches=[]
    process=subprocess.Popen(['git','cat-file','--batch'],cwd=root,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    try:
        for name,value in expected.items():
            process.stdin.write(('HEAD:'+name+'\n').encode('utf-8'));process.stdin.flush()
            header=process.stdout.readline().decode('ascii').strip().split()
            if len(header)!=3 or header[1]!='blob':raise ValueError('Missing committed blob: '+name)
            content=process.stdout.read(int(header[2]));delimiter=process.stdout.read(1)
            if delimiter!=b'\n':raise ValueError('Invalid Git batch framing')
            if hashlib.sha256(content).hexdigest()!=value:mismatches.append(name)
    finally:
        process.stdin.close();process.stdout.close();process.wait(timeout=30)
    result={'status':'passed' if not mismatches else 'failed','checked_files':len(expected),'mismatches':mismatches,
            'workingtree_online_source_unchanged':all(digest(root/n)==h for n,h in plan['online_files'].items()),
            'gitattributes_before_sha256':prior_attributes,'gitattributes_after_sha256':expected['.gitattributes'],
            'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
            'scope':'Git representation repair only; old source bytes remain frozen; no online/evaluation calls'}
    save(audit/'local_checkpoint_index_report.json',result)
    return result


if __name__=='__main__':
    result=verify(ROOT);print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result['status']=='passed' and result['workingtree_online_source_unchanged'] else 1)
