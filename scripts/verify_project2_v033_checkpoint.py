"""Read-only Git blob verification against the pre-commit evidence manifest."""
from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'audit/project2-v1'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8').strip()


def verify() -> dict:
    manifest_path = AUDIT / 'v033_local_checkpoint_manifest.json'
    manifest = read(manifest_path)
    expected = dict(manifest['files'])
    for path, wanted in manifest['online_source'].items():
        if path in expected and expected[path] != wanted:
            raise ValueError('Manifest has conflicting hashes: ' + path)
        expected[path] = wanted
    commit = git('rev-parse', 'HEAD')
    paths = sorted(expected)
    queries = ''.join(f'{commit}:{path}\n' for path in paths).encode('utf-8')
    process = subprocess.run(['git', 'cat-file', '--batch'], input=queries,
                             cwd=ROOT, capture_output=True, check=True)
    stream = process.stdout
    offset = 0
    errors = []
    matched = 0
    for path in paths:
        newline = stream.index(b'\n', offset)
        header = stream[offset:newline].decode('utf-8')
        offset = newline + 1
        if header.endswith(' missing'):
            errors.append({'file': path, 'error': 'missing'})
            continue
        _oid, kind, size_text = header.split()
        size = int(size_text)
        data = stream[offset:offset + size]
        offset += size
        if stream[offset:offset + 1] != b'\n':
            raise ValueError('Malformed Git batch response')
        offset += 1
        actual = digest(data)
        if kind != 'blob' or actual != expected[path]:
            errors.append({'file': path, 'expected': expected[path],
                           'observed': actual, 'kind': kind})
        else:
            matched += 1
    if offset != len(stream):
        raise ValueError('Unconsumed Git output')
    result = {'status': 'passed' if not errors else 'failed', 'commit': commit,
              'checked': len(paths), 'matched': matched, 'errors': errors,
              'manifest_sha256': digest(manifest_path.read_bytes()),
              'evidence_type': '真实运行（本地Git对象只读校验）'}
    (AUDIT / 'v033_committed_bytes.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if errors:
        raise ValueError('Committed blobs differ from frozen evidence manifest')
    gate = read(AUDIT / 'v033_chap13_gate.json')
    held = read(ROOT / 'evals/project2-v1/ch13_v033/heldout_receipt.json')
    count = read(AUDIT / 'v033_count_discrepancy.json')
    receipt = {'observed_at': datetime.now(timezone.utc).isoformat(),
               'commit': commit, 'subject': git('show', '-s', '--format=%s', commit),
               'branch': git('branch', '--show-current'),
               'chap13_gate_status': gate['status'],
               'chap13_gate_passed': sum(x['status'] == 'passed' for x in gate['checks']),
               'chap13_gate_total': len(gate['checks']),
               'heldout_receipt': held,
               's14_status': '未通过',
               'count_exact': {'numerator': count['count_exact_numerator'],
                               'denominator': count['requests']},
               'committed_bytes': result,
               'remote_actions_performed': False,
               'final_resource_diagnosis_and_generated_reports': 'retained after checkpoint; not an amended commit'}
    (AUDIT / 'v033_local_commit_receipt.json').write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    evidence = verify()
    logging.info('committed bytes %s: %s/%s; commit=%s', evidence['status'],
                 evidence['matched'], evidence['checked'], evidence['commit'])
