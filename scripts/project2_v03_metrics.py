"""Supplementary metrics from all preregistered records; never rerun a request."""
from __future__ import annotations
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from project2_v03_calibration import p95, save, digest


def report(folder: Path) -> dict:
    records=[json.loads(x) for x in (folder/'requests.jsonl').read_text(encoding='utf-8').splitlines()]
    results={}
    for path in ('rag_only','combination'):
        rows=[x for x in records if x['path']==path]
        if len(rows)!=150 or len({(x['sample_id'],x['repeat']) for x in rows})!=150:
            raise ValueError('Need all 50 tasks x 3, not a success subset')
        metrics={}
        for key in ('attempts','llm_calls','elapsed_seconds'):
            values=[x[key] for x in rows]
            clusters=defaultdict(list)
            for row in rows: clusters[row['sample_id']].append(row[key])
            keys=sorted(clusters); rng=random.Random(20261005); means=[]; quantiles=[]
            for _ in range(10000):
                sampled=[value for identifier in rng.choices(keys,k=len(keys)) for value in clusters[identifier]]
                means.append(sum(sampled)/len(sampled));quantiles.append(p95(sampled))
            means.sort();quantiles.sort()
            repeats=[]
            for repeat in (1,2,3):
                group=[x[key] for x in rows if x['repeat']==repeat]
                repeats.append({'repeat':repeat,'numerator':sum(group),'denominator':len(group),'mean':sum(group)/len(group),'p95':p95(group)})
            metrics[key]={'numerator':sum(values),'denominator':len(values),'independent_questions':len(keys),
                          'mean':sum(values)/len(values),'range':[min(values),max(values)],'p95':p95(values),
                          'mean_cluster_bootstrap95':[means[249],means[9749]],'p95_cluster_bootstrap95':[quantiles[249],quantiles[9749]],
                          'repeats':repeats,'repeat_mean_range':[min(x['mean'] for x in repeats),max(x['mean'] for x in repeats)]}
        results[path]=metrics
    return {'status':'measured','source_sha256':digest(folder/'requests.jsonl'),'bootstrap_seed':20261005,'bootstrap_replicates':10000,
            'evidence_type':'真实运行','paths':results,'all_failures_retained':True,'heldout_calls':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.parse_args()
    folder=Path(__file__).resolve().parents[1]/'evals/project2-v1/calibration_v03'
    value=report(folder);save(folder/'metrics_ci.json',value)
