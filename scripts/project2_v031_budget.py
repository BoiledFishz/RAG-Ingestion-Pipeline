"""Activate only the first whole uncensored batch, recomputing its formula."""
import argparse
import json
import logging
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from project2_v031_calibration import ROOT, decide_batch, digest, save

sys.path.insert(0,str(ROOT/'enterprise-ai-agent'))
from agents.project2.calibration_profile import selected_evidence


def validate_selected_batch(root: Path) -> tuple[dict,Path]:
    decision,target=selected_evidence(root)
    protocol=json.loads((target/'protocol.json').read_text(encoding='utf-8'))
    rows=[json.loads(x) for x in (target/'requests.jsonl').read_text(encoding='utf-8').splitlines()]
    recalculated=decide_batch(rows,False,protocol)
    if recalculated['status']!='selected' or recalculated['limits']!=decision['limits']:
        raise ValueError('Recomputed uncensored P95 and 16/6 floor differ')
    return decision,target


def activate(root: Path) -> dict:
    decision,target=validate_selected_batch(root)
    folder=root/'evals/project2-v1/calibration_v031'
    value={'status':'frozen','version':'project2-v0.3.1-budget-v1','limits':decision['limits'],
           'selected_batch':decision['selected_batch'],'decision_manifest_sha256':digest(folder/'frozen_manifest.json'),
           'spec_manifest_sha256':decision['spec_manifest_sha256']}
    path=folder/'budget_frozen.json'
    if path.exists() and json.loads(path.read_text(encoding='utf-8'))!=value:raise ValueError('Budget already frozen; no rewrite')
    if not path.exists():save(path,value)
    return value


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    logging.info('Frozen budget: %s',activate(ROOT))
