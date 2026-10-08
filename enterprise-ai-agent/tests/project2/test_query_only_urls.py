"""Official tune requests only; URL text must not grant a comparison slot."""
import json
from pathlib import Path

import pytest

from models.project2 import AnalysisRequest
from tools.techqa_document_query import query_groups

ROOT = Path(__file__).resolve().parents[3]


def test_frozen_ambiguous_url_comparison_requires_clarification():
    registration = json.loads((ROOT / 'specs/project2/v0.3.3/task_preregistration.json').read_text(encoding='utf-8'))
    expected = json.loads((ROOT / 'audit/project2-v1/preflight_report.json').read_text(encoding='utf-8'))['sample_measurements']
    cases = [sample for sample in registration['samples']
             if sample['analysis_operation'] == 'compare_document_counts'
             and 'http' in sample['query']
             and expected[sample['sample_id']].get('error', '').startswith('clarification_required')]
    assert cases
    for sample in cases:
        with pytest.raises(ValueError, match='clarification_required'):
            query_groups(AnalysisRequest(query=sample['query'], analysis_operation=sample['analysis_operation']))
