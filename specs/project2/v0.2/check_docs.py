"""Validate Project 2 SDD documents; never execute the application or evaluation.

Usage: python specs/project2/v0.2/check_docs.py [--freeze-manifest]
Only standard-library file readers, hashes and deterministic query projection are
used. The frozen tune file is read solely to verify original query provenance.
No official answer, label, target ID, held-out content or online module is used.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

STATES = ("completed", "partial", "no_data", "permission_denied", "timeout", "failed")
EVIDENCE_TYPES = {"真实运行", "契约测试(Mock)", "故障注入", "未执行"}
QUOTAS = {"compare": 8, "platform": 8, "identifier": 8, "version": 8, "entity": 8, "no_answer_challenge": 10}
ORACLE_KEYS = {"QUESTION_ID", "DOC_IDS", "ANSWER", "ANSWERABLE", "DOCUMENT", "target_doc_id", "gold_label", "official_answer"}


def validate_revision_scope(docs: Path, project_root: Path) -> list[str]:
    baseline = project_root / "specs/project2/v0.1"
    snapshot = json.loads((project_root / "audit/project2-v1/frozen_spec_snapshot.json").read_text(encoding="utf-8"))
    for relative, expected in snapshot["files"].items():
        ensure(sha256((project_root / relative).read_bytes()) == expected, f"Frozen v0.1 changed: {relative}")
    editable = {"spec.md", "acceptance_scenarios.csv", "check_docs.py"}
    additions = {"approval_addendum.md", "delta.md", "delta.json", "zero_predicate_registration.json", "version_manifest.json"}
    inherited = {p.name for p in baseline.iterdir() if p.is_file()}
    current = {p.name for p in docs.iterdir() if p.is_file()}
    ensure(inherited <= current and current <= inherited | additions, "Revision adds/removes an unauthorized artifact")
    for name in inherited - editable:
        ensure((baseline / name).read_bytes() == (docs / name).read_bytes(), f"Protected inherited artifact changed: {name}")
    old = (baseline / "spec.md").read_text(encoding="utf-8-sig")
    new = (docs / "spec.md").read_text(encoding="utf-8-sig")
    ensure(new.split('<a id="s18">', 1)[0].rstrip() == old.replace("规格 v0.1", "规格 v0.2", 1).rstrip(), "Protected S00–17 text changed")
    ensure(new.count('<a id="s18">') == 1, "Missing unique data-only revision section")
    delta = json.loads((docs / "delta.json").read_text(encoding="utf-8"))
    ensure(delta["from_version"] == "v0.1" and delta["to_version"] == "v0.2" and delta["authorization_date"] == "2026-10-05", "Delta version/date mismatch")
    changes = unique(delta["changes"], "scenario_id")
    ensure(set(changes) == {"AC12-02", "AC12-03"}, "Data revisions exceed independently found conflicts")
    old_rows = unique(load_csv(baseline / "acceptance_scenarios.csv"), "scenario_id")
    new_rows = unique(load_csv(docs / "acceptance_scenarios.csv"), "scenario_id")
    ensure(set(old_rows) == set(new_rows), "Scenario set changed")
    registration = json.loads((docs / "zero_predicate_registration.json").read_text(encoding="utf-8"))
    ensure(registration["seed"] == 20261005 and registration["qa_read"] is False and registration["worker_output_read"] is False and registration["model_calls"] == 0, "Zero selection uses prohibited inputs")
    ensure(registration["literal_patterns"] == {key: json.loads((baseline / "task_preregistration.json").read_text(encoding="utf-8"))["sampling_rules"][key] for key in ("entity_pattern", "version_pattern")}, "Zero selection changed approved literal patterns")
    for index, identifier in enumerate(("AC12-02", "AC12-03")):
        predicate = registration["predicates"][index]
        ensure(predicate["count"] == 0 and predicate["measurement_complete"] is True and all(n > 0 for n in predicate["individual_phrase_counts"]), "Zero case has no real complete-zero/marginal evidence")
        ensure(predicate["phrase_roles"] == ["product_or_component", "version"], "Zero fixture is not a product/version predicate")
        ensure(changes[identifier]["new_predicate"] == [predicate["phrases"]] and changes[identifier]["new_independent_count"] == 0, "Delta disagrees with independent registration")
    for identifier, row in old_rows.items():
        altered = {key: {"old": value, "new": new_rows[identifier][key]} for key, value in row.items() if value != new_rows[identifier][key]}
        if identifier not in changes:
            ensure(not altered, f"Unapproved scene change: {identifier}")
            continue
        ensure(set(altered) == {"input_source_and_selection", "setup"}, f"Protected scene state/gate/evidence changed: {identifier}")
        ensure(altered == changes[identifier]["csv_changes"], f"Delta does not enumerate all edits: {identifier}")
        before = json.loads(row["input_source_and_selection"])
        after = json.loads(new_rows[identifier]["input_source_and_selection"])
        ensure({key: value for key, value in after.items() if key != "analysis_predicates"} == before, "Original question or operation changed")
        ensure(after["analysis_predicates"] == changes[identifier]["new_predicate"], "Data predicate differs from delta")
    zero_hash = sha256((docs / "zero_predicate_registration.json").read_bytes())
    ensure(zero_hash in new and zero_hash in (docs / "approval_addendum.md").read_text(encoding="utf-8"), "Zero registration hash not bound to spec/authorization")
    return [f"PASS 限定修订：{len(changes)}处数据谓词；v0.1 {len(snapshot['files'])}文件未变；S00–17/场景集合/状态/门禁/预算/授权/CL/协议不变", f"PASS 零值登记 SHA256={zero_hash}（数据库预检另行运行，不计系统通过）"]


def artifact_hashes(docs: Path) -> dict[str, str]:
    return {p.name: sha256(p.read_bytes()) for p in sorted(docs.iterdir()) if p.is_file() and p.name not in {"version_manifest.json", "approval_addendum.md"}}


def validate_manifest(docs: Path) -> str:
    raw = (docs / "version_manifest.json").read_bytes()
    manifest = json.loads(raw)
    ensure(manifest["files"] == artifact_hashes(docs), "Version artifact hashes changed")
    digest = sha256(raw)
    ensure(f"版本 manifest SHA256：`{digest}`" in (docs / "approval_addendum.md").read_text(encoding="utf-8"), "Version hash missing from approval addendum")
    return f"PASS v0.2 manifest SHA256={digest}"


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def split(value: str) -> set[str]:
    return {item for item in value.split(";") if item}


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if not fields or len(fields) != len(set(fields)):
            raise ValueError(f"{path.name}: empty or duplicate headers")
        rows = list(reader)
    if not rows or any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError(f"{path.name}: empty table or malformed CSV row")
    return rows


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def unique(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    result = {row[key]: row for row in rows}
    ensure(len(result) == len(rows) and all(result), f"Duplicate/empty {key}")
    return result


def no_actual_evidence(row: dict[str, Any], label: str) -> None:
    ensure(row.get("status") == "待实施", f"{label}: status must be 待实施")
    ensure(row.get("evidence_file") == "", f"{label}: evidence_file must be empty")
    actual_fields = [key for key in row if key.startswith("actual")]
    ensure(bool(actual_fields), f"{label}: missing actual field")
    for field in actual_fields:
        ensure(row[field] == "未执行", f"{label}: {field} must be 未执行")


def matrix_from_spec(spec: str) -> dict[tuple[str, str], str]:
    section = spec.split('id="s07"', 1)[1].split('id="s08"', 1)[0]
    table = [line for line in section.splitlines() if line.startswith("| ")]
    header = [x.strip() for x in table[0].strip("|").split("|")]
    ensure(tuple(header[1:]) == STATES, "S07: invalid DB column order")
    matrix = {}
    for line in table[2:]:
        cells = [x.strip() for x in line.strip("|").split("|")]
        ensure(len(cells) == 7 and cells[0] in STATES, "S07: invalid row")
        for db, overall in zip(STATES, cells[1:]):
            ensure(overall in STATES, "S07: invalid overall state")
            matrix[(cells[0], db)] = overall
    ensure(len(matrix) == 36, "S07: must define all 36 pairs")
    return matrix


def utf16_len(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def query_candidates(source: list[dict[str, Any]], rules: dict[str, str], seed: int) -> list[dict[str, Any]]:
    """Reproduce query-only registration; do not access any oracle field."""
    patterns = {
        name: re.compile(rules[f"{name}_pattern"], re.ASCII | (0 if name == "identifier" else re.IGNORECASE))
        for name in ("entity", "version", "platform", "identifier")
    }
    pool = []
    seen = set()
    for row in source:
        # Access only the two explicitly allowed string values.
        title = row["record"]["QUESTION_TITLE"]
        body = row["record"]["QUESTION_TEXT"]
        ensure(isinstance(title, str) and isinstance(body, str), "Non-string original query")
        query = title + "\n" + body
        digest = sha256(query.encode("utf-8"))
        if digest in seen:
            continue
        seen.add(digest)
        slots = {}
        for name, pattern in patterns.items():
            spans = []
            terms = set()
            for match in pattern.finditer(query):
                term = match.group().lower()
                if term in terms:
                    continue
                terms.add(term)
                spans.append({"text": match.group(), "start": utf16_len(query[:match.start()]), "end": utf16_len(query[:match.end()])})
            slots[{"entity": "entities", "version": "versions", "platform": "platforms", "identifier": "identifiers"}[name]] = spans
        if not slots["entities"]:
            continue
        kind = "compare" if len(slots["versions"]) >= 2 else "platform" if slots["platforms"] else "identifier" if slots["identifiers"] else "version" if slots["versions"] else "entity"
        pool.append({"original_question_title": title, "original_question_text": body, "query": query, "query_sha256": digest, "request_slots": slots, "kind": kind, "selection_key": sha256(f"{seed}:{digest}".encode())})
    return pool


def validate_registration(docs: Path, project_root: Path, spec: str) -> tuple[dict[str, dict[str, Any]], str]:
    path = docs / "task_preregistration.json"
    raw = path.read_bytes()
    digest = sha256(raw)
    sidecar = (docs / "task_preregistration.json.sha256").read_text(encoding="utf-8").split()
    ensure(sidecar == [digest, "task_preregistration.json"], "Registration SHA256 sidecar mismatch")
    ensure(digest in spec, "Registration SHA256 missing/mismatched in spec")
    data = json.loads(raw)
    no_actual_evidence(data, "registration")
    ensure(data["partition"] == "tune" and data["seed"] == 20261005, "Registration partition/seed mismatch")
    ensure(data["input_projection"] == ["QUESTION_TITLE", "QUESTION_TEXT"], "Registration must use query-only projection")
    ensure(data["quotas"] == QUOTAS and data["evaluation_runs"] == 0, "Registration quota/run-count mismatch")
    ensure(data["protocol_version"] == "techqa-query-task-v1", "Registration rule version mismatch")
    ensure(data["source"] == "evals/protocol_v0/tune.json", "Only frozen tune source is allowed")
    source_bytes = (project_root / data["source"]).read_bytes()
    ensure(sha256(source_bytes) == data["source_sha256"], "Frozen tune source hash mismatch")
    pool = query_candidates(json.loads(source_bytes), data["sampling_rules"], data["seed"])
    expected = []
    for kind in ("compare", "platform", "identifier", "version", "entity"):
        eligible = sorted((x for x in pool if x["kind"] == kind), key=lambda x: x["selection_key"])
        ensure(len(eligible) >= QUOTAS[kind], f"Insufficient {kind} candidates")
        for index, item in enumerate(eligible[:QUOTAS[kind]], 1):
            expected.append({**item, "sample_id": f"P2-{kind.upper()}-{index:02}", "stratum": kind, "ordinal": index})
    used = {item["query_sha256"] for item in expected}
    challenge = sorted((x for x in pool if x["query_sha256"] not in used), key=lambda x: (utf16_len(x["query"]), x["selection_key"]))
    ensure(len(challenge) >= QUOTAS["no_answer_challenge"], "Insufficient challenge candidates")
    for index, item in enumerate(challenge[:QUOTAS["no_answer_challenge"]], 1):
        expected.append({**item, "sample_id": f"P2-NOANSWER-{index:02}", "stratum": "no_answer_challenge", "ordinal": index})
    samples = data["samples"]
    ensure(len(samples) == 50, "Expected 50 preregistered original queries")
    ensure(Counter(x["stratum"] for x in samples) == Counter(QUOTAS), "Stratum counts mismatch")
    for actual, expected_item in zip(samples, expected):
        no_actual_evidence(actual, actual["sample_id"])
        ensure(not (set(actual) & ORACLE_KEYS), "Oracle field in registered sample")
        for key, value in expected_item.items():
            if key != "kind":
                ensure(actual.get(key) == value, f"{actual['sample_id']}: deterministic selection/query mismatch in {key}")
        operation = "compare_document_counts" if actual["stratum"] == "compare" else "document_count"
        ensure(actual["analysis_operation"] == operation, "Sample operation mismatch")
    return unique(samples, "sample_id"), digest


def validate(docs: Path, project_root: Path, *, freezing: bool = False) -> list[str]:
    scope_output = validate_revision_scope(docs, project_root)
    requirements_bytes = (docs / "requirements_v0.1.md").read_bytes()
    digest = sha256(requirements_bytes)
    requirements_text = requirements_bytes.decode("utf-8-sig")
    requirement_rows = {}
    for line_number, line in enumerate(requirements_text.splitlines(), 1):
        match = re.match(r"^\| ([A-Z]+-\d{2}) \| (.*?) \| (.*?) \|$", line)
        if match:
            ensure(match[1] not in requirement_rows, f"Duplicate source requirement {match[1]}")
            requirement_rows[match[1]] = (line_number, match[2], match[3])
    ensure(bool(requirement_rows), "No requirement IDs found in source")
    trace = unique(load_csv(docs / "traceability.csv"), "requirement_id")
    scenarios = unique(load_csv(docs / "acceptance_scenarios.csv"), "scenario_id")
    spec = (docs / "spec.md").read_text(encoding="utf-8-sig")
    ensure(digest in spec, "Requirements SHA256 mismatched/missing in spec")
    matrix = matrix_from_spec(spec)
    task_text = (docs / "tasks.md").read_text(encoding="utf-8-sig")
    task_rows = [line for line in task_text.splitlines() if re.match(r"^\| T\d{2}-\d{2} \|", line)]
    task_ids = {line.split("|")[1].strip() for line in task_rows}
    ensure(len(task_rows) == len(task_ids) and all(line.strip().endswith("| 待实施 |") for line in task_rows), "Tasks must be unique and 待实施")
    ensure(set(requirement_rows) <= set(trace), f"Missing requirement IDs: {sorted(set(requirement_rows)-set(trace))}")
    samples, registration_digest = validate_registration(docs, project_root, spec)
    for identifier, row in trace.items():
        no_actual_evidence(row, identifier)
        ensure(row["requirements_sha256"] == digest, f"{identifier}: requirements SHA256 mismatch")
        sources = row["source"].split(";")
        ensure(sources[0] == "requirements_v0.1.md", f"{identifier}: source must reference local copy")
        for source in sources:
            name, _, anchor = source.partition("#")
            target = docs / name
            ensure(target.is_file() and target.resolve().is_relative_to(docs), f"{identifier}: dangling/unsafe source {source}")
            if anchor:
                ensure(f'id="{anchor}"' in target.read_text(encoding="utf-8-sig"), f"{identifier}: missing source anchor")
        if identifier in requirement_rows:
            number, text, chapter = requirement_rows[identifier]
            ensure(row["origin_type"] == "统一需求" and row["source"] == "requirements_v0.1.md", f"{identifier}: incorrect origin")
            ensure(row["requirement"] == text and int(row["source_line"]) == number and row["source_chapter"] == chapter, f"{identifier}: source text/line/chapter mismatch")
        else:
            ensure(row["origin_type"] == "用户补充" and len(sources) > 1, f"{identifier}: supplementary origin must be explicit")
        ensure(split(row["task_ids"]) <= task_ids and bool(split(row["task_ids"])), f"{identifier}: dangling task")
        for section in split(row["spec_section"]):
            ensure(section.startswith("spec.md#") and f'id="{section.split("#", 1)[1]}"' in spec, f"{identifier}: dangling spec section")
        linked_ids = split(row["scenario_ids"])
        ensure(linked_ids and linked_ids <= set(scenarios), f"{identifier}: dangling scenario reference")
        linked = [scenarios[x] for x in linked_ids]
        ensure(all(identifier in split(case["requirement_ids"]) for case in linked), f"{identifier}: missing reciprocal scenario reference")
        for field in ("planned_test", "planned_evidence_type", "planned_evidence_file"):
            expected = {case[field] for case in linked}
            ensure(split(row[field]) == expected, f"{identifier}: {field} disagrees with linked scenarios")
    overall_states = set()
    for identifier, row in scenarios.items():
        no_actual_evidence(row, identifier)
        linked = split(row["requirement_ids"])
        ensure(linked and linked <= set(trace), f"{identifier}: dangling requirement reference")
        ensure(all(identifier in split(trace[x]["scenario_ids"]) for x in linked), f"{identifier}: missing reciprocal requirement reference")
        workers = re.fullmatch(r"RAG=([a-z_]+);DB=([a-z_]+)", row["expected_worker_states"])
        ensure(workers is not None and workers[1] in STATES and workers[2] in STATES, f"{identifier}: explicit six-state Worker pair required")
        pair = (workers[1], workers[2])
        cell = f"S07[rag={pair[0]},db={pair[1]}]"
        ensure(row["matrix_cell"] == cell and cell in row["assertions"], f"{identifier}: missing/extraneous S07 matrix cell")
        overall = row["expected_overall_status"]
        # Exact states or one explicit matrix cell are allowed; no vague prose.
        ensure(overall in STATES or overall == cell, f"{identifier}: invalid overall status")
        ensure(overall == cell or matrix[pair] == overall, f"{identifier}: overall disagrees with S07 cell")
        overall_states.add(matrix[pair] if overall == cell else overall)
        ensure(not re.search(r"占位|待选|后续仅从|TBD|TODO|<query>|依\s*S07", row["input_source_and_selection"], re.IGNORECASE), f"{identifier}: placeholder input")
        request = json.loads(row["input_source_and_selection"])
        allowed = {"sample_id", "query", "analysis_operation", "include_samples", "sample_limit"}
        if identifier in {"AC12-02", "AC12-03"}:
            allowed.add("analysis_predicates")
        ensure(set(request) == allowed, f"{identifier}: unexpected/oracle request keys")
        ensure(request["sample_id"] == row["input_sample_id"] and row["input_sample_id"] in samples, f"{identifier}: dangling sample")
        original = samples[row["input_sample_id"]]
        ensure(request["query"] == original["query"] and request["analysis_operation"] == original["analysis_operation"], f"{identifier}: changed/nonofficial query or operation")
        ensure(request["include_samples"] is True and type(request["sample_limit"]) is int and request["sample_limit"] == 5, f"{identifier}: invalid sample limit")
        ensure(row["planned_evidence_type"] in EVIDENCE_TYPES and row["planned_test"] and row["planned_evidence_file"], f"{identifier}: missing/invalid planned evidence")
        ensure(not re.search(r"TBD|TODO|待填写", row["planned_test"]), f"{identifier}: placeholder planned test")
    ensure(overall_states == set(STATES), "Scenarios must cover all six overall states")
    for identifier in ("AC12-11", "AC12-13"):
        ensure(scenarios[identifier]["mandatory_gate"] == "必过" and scenarios[identifier]["planned_evidence_type"] in {"真实运行", "故障注入"}, f"{identifier}: core Worker mandatory gate missing")
    no_answer = scenarios["AC12-23"]
    ensure(no_answer["planned_evidence_type"] == "真实运行" and no_answer["input_sample_id"] == "P2-NOANSWER-01" and no_answer["matrix_cell"] == "S07[rag=no_data,db=completed]", "Missing preregistered real no-answer combination")
    review = (docs / "review_sheet.md").read_text(encoding="utf-8-sig")
    for field in ("审阅人", "审阅日期", "批准版本哈希"):
        ensure(re.search(rf"^{field}：\s*_{{3,}}\s*$", review, re.MULTILINE) is not None, f"Review sheet: {field} must remain blank")
    ensure(len(review.splitlines()) <= 40 and len(review) <= 1800, "Review sheet exceeds compact one-page limit")
    output = [
        f"PASS 需求覆盖：{len(requirement_rows)}/{len(requirement_rows)}；追踪项：{len(trace)}；双向引用无悬空",
        f"PASS 场景：{len(scenarios)}；S07矩阵：{len(matrix)}单元；六状态覆盖；具体原问题输入无占位",
        "PASS 查询侧登记：50条（8/8/8/8/8/10）；确定性抽样/原问题/哈希一致",
        f"PASS 全部status=待实施；actual=未执行；evidence_file为空；任务={len(task_ids)}",
        "PASS 计划测试/证据类型/路径集合一致；AC12-11/13必过；确认单签署栏为空",
        f"PASS requirements_v0.1.md SHA256={digest}",
        f"PASS task_preregistration.json SHA256={registration_digest}",
        "PASS 文档检查通过；模型/检索/数据库/评测调用=0",
    ]
    output.extend(scope_output)
    if not freezing:
        output.append(validate_manifest(docs))
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--freeze-manifest", action="store_true", help="Freeze only after all structure/scope checks pass; never overwrite a manifest")
    args = parser.parse_args()
    try:
        docs = args.docs_dir.resolve()
        if args.freeze_manifest:
            ensure(not (docs / "version_manifest.json").exists(), "Version manifest already frozen; refusing overwrite")
            validate(docs, args.project_root.resolve(), freezing=True)
            manifest = {"version": "v0.2", "authorization_date": "2026-10-05", "files": artifact_hashes(docs), "excluded": ["version_manifest.json", "approval_addendum.md"], "exclusion_reason": "Avoid recursive self/authorization hash; addendum quotes this manifest hash"}
            path = docs / "version_manifest.json"
            path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            approval = docs / "approval_addendum.md"
            text = approval.read_text(encoding="utf-8")
            ensure(text.count("版本 manifest SHA256：待生成") == 1, "Version hash placeholder not unique")
            approval.write_text(text.replace("版本 manifest SHA256：待生成", f"版本 manifest SHA256：`{sha256(path.read_bytes())}`"), encoding="utf-8")
        output = validate(docs, args.project_root.resolve())
    except (ValueError, KeyError, IndexError, OSError, TypeError) as error:
        sys.stdout.write(f"FAIL {error}\n")
        return 1
    sys.stdout.write("\n".join(output) + "\n")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
