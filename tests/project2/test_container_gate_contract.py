"""A claimed or incomplete container pass cannot satisfy the fixed gate."""
def test_container_gate_rejects_missing_or_false_observations():
    from scripts.run_project2_container_gate import REQUIRED, verdict
    report={'checks':[{'check':name,'expected':True,'observed':True} for name in REQUIRED]}
    assert verdict(report)=='passed'
    report['checks'][0]['observed']=False
    assert verdict(report)=='failed'
    report['checks'].pop(0)
    assert verdict(report)=='failed'
