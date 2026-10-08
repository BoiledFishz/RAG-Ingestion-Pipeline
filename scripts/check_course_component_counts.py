"""Independent read-only evidence for the registered literal-component conflict.

No Worker/catalogue imports, model calls, QA targets, official answers or labels.
This proposes data expectations; it never edits or approves frozen records.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'audit/project2-course-completion-20261007'
LOGGER = logging.getLogger(__name__)


def phrase_expression(phrases: list[str]) -> str:
    return ' AND '.join('"' + text.replace('"', '""') + '"' for text in phrases)


def inspect() -> dict:
    registered = ROOT / 'specs/project2/v0.3.3/task_preregistration.json'
    registration = json.loads(registered.read_text(encoding='utf-8'))
    old = json.loads((ROOT / 'audit/project2-v1/preflight_report.json').read_text(encoding='utf-8'))
    component_name = re.compile(r'\b[A-Z][A-Z0-9_]{1,11}\b', re.ASCII)
    version = re.compile(r'\b(?:V(?:ersion)?\s*\d+(?:\.\d+)*|Release\s*\d+|\d+\.\d+(?:\.\d+)*)\b', re.IGNORECASE | re.ASCII)
    # These denote syntax, transport and diagnostics rather than products.
    # An API version may belong to the preceding explicit component.
    markers = {'ERROR', 'WARNING', 'INFO', 'ANSWER', 'QUESTION', 'HTTP', 'HTTPS', 'URL', 'SQL', 'XML', 'IP', 'ID', 'QID', 'SSL', 'INSTALLATION', 'EXIT', 'REQUESTED', 'TERMINATION', 'REASON', 'CODE', 'API', 'NET'}
    rows = []
    database = ROOT / '.rag_data/techqa_full.sqlite'
    with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as connection:
        connection.execute('PRAGMA query_only=ON')
        manifest = dict(connection.execute('SELECT key,value FROM manifest'))
        if manifest.get('scope') != 'full' or manifest.get('complete') != 'true':
            raise ValueError('Incomplete official full corpus')
        for sample in registration['samples']:
            expectation = old['sample_measurements'][sample['sample_id']]
            if sample['analysis_operation'] != 'compare_document_counts' or not expectation.get('error', '').startswith('clarification_required'):
                continue
            query = sample['query']
            view = re.sub(r'https?://[^\s<>]+|www\.[^\s<>]+', lambda match: ' ' * len(match.group()), query, flags=re.IGNORECASE)
            groups = []
            names = [match for match in component_name.finditer(view) if match.group() not in markers]
            for index, name in enumerate(names):
                end = min(name.end() + 32, names[index + 1].start() if index + 1 < len(names) else len(view))
                number = version.search(view, name.end(), end)
                if number:
                    value = [query[name.start():name.end()], query[number.start():number.end()]]
                    if value not in groups:
                        groups.append(value)
            if len(groups) != 2:
                continue
            counts = [connection.execute('SELECT COUNT(DISTINCT d.doc_id) FROM docs AS d JOIN search AS s ON d.rowid=s.rowid WHERE search MATCH ?', (phrase_expression(group),)).fetchone()[0] for group in groups]
            a, b = (phrase_expression(group) for group in groups)
            overlap = connection.execute('SELECT COUNT(*) FROM (SELECT d.doc_id FROM docs AS d JOIN search AS s ON d.rowid=s.rowid WHERE search MATCH ? INTERSECT SELECT d.doc_id FROM docs AS d JOIN search AS s ON d.rowid=s.rowid WHERE search MATCH ?)', (a, b)).fetchone()[0]
            rows.append({'sample_id': sample['sample_id'], 'query_sha256': hashlib.sha256(query.encode()).hexdigest(),
                         'frozen_expectation': expectation, 'independent_literal_predicates': groups,
                         'independent_counts': counts, 'intersection': overlap,
                         'delta_a_minus_b': counts[0] - counts[1],
                         'status': 'proposal_pending_user_approval'})
    result = {'observed_at': datetime.now(timezone.utc).isoformat(), 'evidence_type': '真实运行（官方全文库独立只读复算）',
              'worker_or_catalogue_code_reused': False, 'official_qa_fields_used': [], 'llm_calls': 0, 'heldout_calls': 0,
              'registered_tasks_sha256': hashlib.sha256(registered.read_bytes()).hexdigest(),
              'data_manifest': manifest, 'differences': rows,
              'approved_records_modified': False, 'quality_acceptance': '未通过；等待解决规格/冻结预期冲突'}
    AUDIT.mkdir(exist_ok=True)
    result['proposal_version'] = 2
    result['prior_draft'] = 'component_expectation_proposal.json: discarded, API is a syntax marker rather than the component; original read-only observation retained'
    (AUDIT / 'component_expectation_proposal_v2.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    LOGGER.info('Independent full-corpus component proposals=%d; frozen files unchanged', len(rows))
    return result


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    inspect()
