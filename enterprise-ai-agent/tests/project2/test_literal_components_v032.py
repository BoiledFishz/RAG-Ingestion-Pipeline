import json
from pathlib import Path
from models.project2 import AnalysisRequest
from tools.techqa_document_query import query_groups
ROOT=Path(__file__).resolve().parents[3]

def test_official_portal_queries_keep_literal_product():
    partitions=json.loads((ROOT/'splits.json').read_text(encoding='utf-8'))['partitions']
    rows=json.loads((ROOT/partitions['tune']['file']).read_text(encoding='utf-8'))
    from evaluation_protocol.storage import query
    queries=[query(x['record']) for x in rows]
    cases=[q for q in queries if 'Portal' in q and 'CF14' in q and 'WebSphere' not in q]
    assert len(cases)>=2
    for q in cases:
        groups=query_groups(AnalysisRequest(query=q))
        assert groups[0][0]=='Portal'
        assert all(term in q for term in groups[0])

def test_known_product_does_not_hide_other_literal_components():
    samples=json.loads((ROOT/'specs/project2/v0.3.2/task_preregistration.json').read_text(encoding='utf-8'))['samples']
    sample=next(x for x in samples if x['analysis_operation']=='compare_document_counts' and 'ICC 4.0.1' in x['query'])
    groups=query_groups(AnalysisRequest(query=sample['query'],analysis_operation=sample['analysis_operation']))
    assert len(groups)==2
    assert ['ICC','4.0.1'] in groups
    assert any(group[-1]=='5.2.1.2' for group in groups)
    assert all(term in sample['query'] for group in groups for term in group)
