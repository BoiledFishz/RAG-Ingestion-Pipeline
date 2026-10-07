"""Read-only tune discrepancy disclosure; never revise frozen expectations."""
from __future__ import annotations
import json
import re
from pathlib import Path
from project2_v03_report import read, save, sha

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    rows_path = ROOT / 'evals/project2-v1/ch13_v033/business/scored.json'
    reference_path = ROOT / 'audit/project2-v1/preflight_report.json'
    protocol_path = ROOT / 'evals/project2-v1/calibration_v031/protocol.json'
    reference = read(reference_path)['sample_measurements']
    samples = {s['sample_id']: s for s in read(protocol_path)['samples']}
    rows = read(rows_path)
    differences = []
    for row in rows:
        if row['count_exact']:
            continue
        sample = samples[row['sample_id']]
        worker = row['result']['workers']['database']
        groups = worker['payload']['groups']
        url_spans = [(m.start(), m.end()) for m in re.finditer(r'https?://\S+', sample['query'])]
        url_only_terms = []
        for group in groups:
            for term in group['predicate']:
                matches = list(re.finditer(re.escape(term), sample['query'], re.IGNORECASE))
                if matches and all(any(a <= m.start() and m.end() <= b for a, b in url_spans) for m in matches):
                    url_only_terms.append(term)
        differences.append({'sample_id': row['sample_id'], 'repeat': row['repeat'],
            'query_sha256': sample['query_sha256'], 'frozen_expectation': reference[row['sample_id']],
            'observed_worker_status': worker['status'],
            'observed_groups': [{'predicate': g['predicate'], 'count': g['count']} for g in groups],
            'observed_rules_version': worker['payload']['request_slots_version'],
            'terms_occurring_only_inside_url': url_only_terms,
            'attribution': 'v032 component fallback differs from the frozen preflight predicate derivation',
            'classification': 'predicate/clarification discrepancy; not evidence of a numerically wrong SQL count'})
    output = {'scope': '仅 tune/对照集，非 held-out 验证', 'evidence_type': '真实运行（只读已有记录）',
        'requests': len(rows), 'count_exact_numerator': sum(r['count_exact'] for r in rows),
        'discrepant_observations': len(differences),
        'discrepant_tasks': len({r['sample_id'] for r in differences}), 'differences': differences,
        'source_files': {p.relative_to(ROOT).as_posix(): sha(p) for p in (rows_path, reference_path, protocol_path)},
        'official_or_frozen_expectations_changed': False, 'new_inference_calls': 0,
        'heldout_content_read': False, 'design_changed': False,
        'quality_acceptance': '未通过；不以工程状态或真实计数替代谓词正确性',
        'current_chap13_gate': 'unchanged 15 checks; no new or relaxed gate added',
        'action': 'disclose discrepancy, preserve 144/150, continue only under existing S14-failure continuation authorization'}
    target = ROOT / 'audit/project2-v1/v033_count_discrepancy.json'
    if target.exists():
        if read(target) != output:
            raise ValueError('Count diagnosis already frozen')
    else:
        save(target, output)
    print(json.dumps({k: output[k] for k in ('requests', 'count_exact_numerator', 'discrepant_observations', 'discrepant_tasks', 'new_inference_calls')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
