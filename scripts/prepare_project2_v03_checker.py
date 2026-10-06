"""Generate v0.3 checker retaining v0.2 structural checks, with A/B-only scope."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
old = (ROOT / 'specs/project2/v0.2/check_docs.py').read_text(encoding='utf-8')
start = old.index('def validate_revision_scope(')
end = old.index('\ndef artifact_hashes(', start)
replacement = r'''def validate_revision_scope(docs: Path, project_root: Path) -> list[str]:
    baseline = project_root / "specs/project2/v0.2"
    protocol_path = project_root / "evals/project2-v1/calibration_v03/protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    for name, expected in protocol["protected_files"].items():
        ensure(sha256((project_root / name).read_bytes()) == expected, f"Protected v0.1/v0.2 changed: {name}")
    inherited = {p.name for p in baseline.iterdir() if p.is_file()}
    current = {p.name for p in docs.iterdir() if p.is_file()}
    ensure(current in (inherited, inherited - {"version_manifest.json"}), "Scenario/artifact set adds or removes unapproved file")
    editable = {"spec.md", "tasks.md", "clarifications.md", "acceptance_scenarios.csv", "check_docs.py", "approval_addendum.md", "delta.md", "delta.json", "version_manifest.json"}
    for name in inherited - editable:
        ensure((baseline / name).read_bytes() == (docs / name).read_bytes(), f"Protected inherited artifact changed: {name}")
    delta = json.loads((docs / "delta.json").read_text(encoding="utf-8"))
    ensure(delta["from_version"] == "v0.2" and delta["to_version"] == "v0.3" and delta["authorization_date"] == "2026-10-05", "Revision version/authorization mismatch")
    ensure(delta["attempt_definition_changed"] is False, "Attempt definition cannot shrink counts")
    ensure(delta["calibration_protocol_sha256"] == sha256(protocol_path.read_bytes()), "Calibration registration changed")
    old_spec = (baseline / "spec.md").read_text(encoding="utf-8-sig")
    new_spec = (docs / "spec.md").read_text(encoding="utf-8-sig")
    def protected_spec(text: str) -> str:
        a = text.index('<a id="s08">'); b = text.index('<a id="s09">')
        text = text[:a] + "AUTHORIZED_BUDGET_SECTION\n" + text[b:]
        a = text.index('**AC12-23'); b = text.index('\n\n', a)
        return (text[:a] + "AUTHORIZED_AC12_23\n" + text[b:]).replace("规格 v0.3", "规格 v0.2", 1)
    ensure(protected_spec(old_spec) == protected_spec(new_spec), "Protected spec outside S08/AC12-23 changed")
    ensure(matrix_from_spec(old_spec) == matrix_from_spec(new_spec), "Protected S07 changed")
    for name, allowed in (("tasks.md", {"| T12-06 |", "| T12-09 |"}), ("clarifications.md", {"| CL-08 |"})):
        before = (baseline/name).read_text(encoding="utf-8-sig").splitlines()
        after = (docs/name).read_text(encoding="utf-8-sig").splitlines()
        ensure(len(before) == len(after), f"Protected {name} structure changed")
        for left,right in zip(before,after):
            ensure(left == right or any(left.startswith(prefix) and right.startswith(prefix) for prefix in allowed), f"Unapproved {name} line change")
    before = unique(load_csv(baseline / "acceptance_scenarios.csv"), "scenario_id")
    after = unique(load_csv(docs / "acceptance_scenarios.csv"), "scenario_id")
    ensure(before.keys() == after.keys(), "Scenario set changed")
    allowed_cells = {"AC12-01": {"setup"}, "AC12-15": {"setup", "assertions"}, "AC12-16": {"setup"},
                     "AC12-23": {"scenario", "setup", "action", "assertions", "expected_worker_states", "expected_overall_status", "matrix_cell"}}
    recorded = {x["scenario_id"]: x["cells"] for x in delta["changes"] if "scenario_id" in x}
    for key,row in before.items():
        edits = {k: {"old": value, "new": after[key][k]} for k,value in row.items() if value != after[key][k]}
        ensure(set(edits) <= allowed_cells.get(key, set()), f"Unapproved scenario cell changed: {key}")
        ensure(edits == recorded.get(key, {}), f"Delta does not record exact scene edits: {key}")
    ensure(before["AC12-03"] == after["AC12-03"], "Protected dual-no_data Mock changed")
    for name in ("spec.md", "tasks.md", "clarifications.md"):
        expected = (baseline/name).read_text(encoding="utf-8-sig")
        for change in delta["changes"]:
            if change["file"] == name:
                ensure(expected.count(change["old"]) == 1, f"Delta old span ambiguous: {name}")
                expected = expected.replace(change["old"], change["new"])
        ensure(expected == (docs/name).read_text(encoding="utf-8-sig"), f"Delta does not enumerate all text edits: {name}")
    ensure(len(protocol["samples"]) == 50 and len(protocol["n_samples"]) == 183 and protocol["repeats"] == 3, "Calibration/N cohort incomplete")
    ensure(len({x["sample_id"] for x in protocol["n_samples"]}) == 183, "N records removed/duplicated")
    ensure(protocol["protected_files"] and protocol["heldout_calls"] == 0, "Registration omitted protected hashes/held-out boundary")
    return [f"PASS A/B限定修订={len(delta['changes'])}条；v0.1/v0.2文件不变；S07/42场景/授权/范围/CL01–07/冻结协议保持", "PASS 完整50任务×3×2标定及全部183条tune N×3预登记；无输出后筛选；AC12-03原样"]

'''
text = old[:start] + replacement + old[end:]
text = text.replace('no_answer["matrix_cell"] == "S07[rag=no_data,db=completed]", "Missing preregistered real no-answer combination"', 'no_answer["matrix_cell"] == "S07[rag=observed,db=observed]", "Missing retained real state/quality combination"')
text = text.replace('v0.2/check_docs.py', 'v0.3/check_docs.py').replace('PASS v0.2 manifest', 'PASS v0.3 manifest').replace('"version": "v0.2",', '"version": "v0.3",')
a = text.index('        workers = re.fullmatch(')
b = text.index('        ensure(not re.search(', a)
normal = text[a:b]
special = '''        if identifier == "AC12-23":
            cell = "S07[rag=observed,db=observed]"
            ensure(row["expected_worker_states"] == "RAG=observed;DB=observed" and row["matrix_cell"] == cell and row["expected_overall_status"] == cell, "AC12-23 must use observed-state matrix lookup")
            ensure(cell in row["assertions"] and "非门禁" in row["assertions"], "State consistency and quality must be separate")
        else:
'''
text = text[:a] + special + ''.join('    '+line+'\n' for line in normal.splitlines()) + text[b:]
(ROOT / 'specs/project2/v0.3/check_docs.py').write_text(text, encoding='utf-8')
