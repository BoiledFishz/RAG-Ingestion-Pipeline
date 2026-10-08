"""No prose claim can turn an incomplete system gate or S14 into a pass."""
def test_course_gate_summary_refuses_claim_only():
    from scripts.project2_course_report import gate_status
    assert gate_status({'status':'passed','checks':[]})=='failed'
    assert gate_status(None)=='not_executed'
