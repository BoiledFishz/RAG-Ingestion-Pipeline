import asyncio
import json
import pytest
from pydantic import ValidationError
from agents.project2.budget import Budget
from models.project2 import AnalysisRequest
from tools.techqa_document_query import DatabaseWorker
from tests.project2.test_core import ROOT, original_sample, owner


def test_distinct_count_and_sample_limit():
    sample=original_sample('P2-ENTITY-01')
    expected=json.loads((ROOT/'audit/project2-v1/preflight_report.json').read_text(encoding='utf-8'))['sample_measurements'][sample['sample_id']]['counts']
    for limit in (0,1,5,10):
        result=asyncio.run(DatabaseWorker(ROOT/'.rag_data/techqa_full.sqlite').run(
            AnalysisRequest(query=sample['query'],sample_limit=limit),owner(),Budget(),'sample-limit-'+str(limit)))
        assert [x['count'] for x in result.payload['groups']]==expected
        assert sum(len(x['samples']) for x in result.payload['groups'])<=limit
        assert result.payload['unit']=='original_document'


def test_overlap_and_partial_comparison():
    from tests.project2.test_core import test_real_overlap_and_partial_use_independent_counts
    test_real_overlap_and_partial_use_independent_counts()


def test_query_allowlist_and_scope():
    sample=original_sample('P2-ENTITY-01')
    for updates in ({'analysis_operation':'SELECT 1'},{'sample_limit':11},{'analysis_predicates':[['x'*121]]}):
        with pytest.raises(ValidationError):AnalysisRequest(query=sample['query'],**updates)


def test_zero_and_unknown():
    from tests.project2.test_core import test_real_zero_not_null, test_real_wrong_scope_fails_with_null
    test_real_zero_not_null();test_real_wrong_scope_fails_with_null()
