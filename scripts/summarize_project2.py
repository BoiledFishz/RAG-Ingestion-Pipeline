"""Generate the Project 2 one-page report from frozen traceability and evidence.

Never converts a claimed pass or a specification preflight into a system pass.
Writes a machine-readable report, a separate runtime trace, and resume progress;
does not edit approved specifications, original QA, or old evaluation ledgers.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage_verdict(report: dict[str, Any] | None) -> str:
    if report is None:
        return "not_executed"
    checks = report.get("checks", [])
    if not checks:
        return "failed"
    for check in checks:
        if "expected_count" in check:
            if check.get("measurement_complete") is not True or check.get("actual_count") != check["expected_count"]:
                return "failed"
        elif "observed" in check and "expected" in check:
            if check["observed"] != check["expected"]:
                return "failed"
        else:
            # A prose claim without a machine-checkable predicate is no pass.
            return "failed"
        if check.get("status") != "passed":
            return "failed"
    if report.get("system_gate_executed") is not True or report.get("gate_scope") != "system_gate":
        return "not_executed"
    return "passed"


def read_json(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def junit_counts(path: Path) -> dict[str, int] | None:
    if not path.is_file():
        return None
    cases = ET.parse(path).getroot().findall(".//testcase")
    return {
        "tests": len(cases),
        "failures": sum(case.find("failure") is not None for case in cases),
        "errors": sum(case.find("error") is not None for case in cases),
        "skipped": sum(case.find("skipped") is not None for case in cases),
    }


def git_value(root: Path, *arguments: str) -> str:
    result = subprocess.run(["git", *arguments], cwd=root, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def enforce_frozen_documents(root: Path, audit: Path) -> dict[str, Any]:
    docs = root / "specs/project2/v0.1"
    current = {path.relative_to(root).as_posix(): sha256(path) for path in sorted(docs.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}
    path = audit / "frozen_spec_snapshot.json"
    snapshot = read_json(path)
    if snapshot is None:
        snapshot = {"captured_at": datetime.now(timezone.utc).isoformat(), "files": current}
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif snapshot["files"] != current:
        raise ValueError("Approved specification files changed since execution snapshot; stop, do not rewrite the snapshot")
    return snapshot


def revision_details(root: Path) -> dict[str, Any]:
    docs = root / "specs/project2/v0.2"
    if not docs.is_dir():
        return {"version": "v0.1", "delta_count": 0, "changes": []}
    audit = root / "audit/project2-v1"
    snapshot = enforce_frozen_documents(root, audit)
    manifest = read_json(docs / "version_manifest.json")
    if manifest is None or any(sha256(docs / name) != digest for name, digest in manifest["files"].items()):
        raise ValueError("v0.2 version manifest missing or changed")
    digest = sha256(docs / "version_manifest.json")
    if digest not in (docs / "approval_addendum.md").read_text(encoding="utf-8"):
        raise ValueError("v0.2 manifest hash not in authorization addendum")
    delta = read_json(docs / "delta.json")
    return {"version": "v0.2", "delta_count": len(delta["changes"]), "changes": delta["changes"],
            "version_manifest_sha256": digest, "v01_unchanged": True,
            "v01_frozen_files": len(snapshot["files"]), "manifest_files": len(manifest["files"])}


def latest_native_gate(audit: Path) -> tuple[dict[str, Any] | None, str | None]:
    candidates = sorted(audit.glob("native_gate_round[0-2].json"))
    if not candidates:
        return None, None
    path = candidates[-1]
    result = read_json(path)
    if path.stem != f"native_gate_round{result['repair_rounds']}":
        raise ValueError("Native repair counter/file mismatch")
    return result, path.name


def wilson(success: int, total: int) -> list[float] | None:
    if not total:
        return None
    z = 1.959963984540054
    p = success / total
    center = (p + z*z/(2*total))/(1+z*z/total)
    margin = z*math.sqrt(p*(1-p)/total + z*z/(4*total*total))/(1+z*z/total)
    return [max(0.0, center-margin), min(1.0, center+margin)]


def component_evidence(audit: Path) -> list[dict[str, Any]]:
    """Derive partial evidence from individual passing checks, not prose totals."""
    mapping = {
        "test_real_db_is_independent_and_exact": ("AC12-12", "真实运行"),
        "test_real_zero_not_null": ("AC12-02", "真实运行"),
        "test_real_overlap_and_partial_use_independent_counts": ("AC12-11", "故障注入"),
        "test_real_wrong_scope_fails_with_null": ("AC12-06", "故障注入"),
        "test_attempt_17_and_llm_7_never_start": ("AC12-15", "契约测试(Mock)"),
        "test_direct_worker_cannot_bypass_budget_or_policy": ("AC12-15", "契约测试(Mock)"),
        "test_request_preserves_query_and_rejects_oracle_or_sql": ("AC12-08", "契约测试(Mock)"),
        "test_all_36_pairs_match_frozen_matrix": ("AC12-14", "契约测试(Mock)"),
        "test_default_route_has_server_auth_and_no_budget_bypass": ("AC12-04", "契约测试(Mock)"),
        "test_independent_legal_db_can_run_if_rag_denied": ("AC12-07", "契约测试(Mock)"),
    }
    path = audit / "ch12_component_checks.junit.xml"
    if not path.is_file():
        return []
    result = []
    for case in ET.parse(path).getroot().findall(".//testcase"):
        if case.get("name") in mapping and not any(case.find(x) is not None for x in ("failure", "error", "skipped")):
            scenario, evidence_type = mapping[case.get("name")]
            result.append({"test": case.get("name"), "scenario_id": scenario, "evidence_type": evidence_type,
                           "evidence_file": "audit/project2-v1/ch12_component_checks.junit.xml", "coverage": "partial_only;not_full_scenario_or_stage"})
    return result


def generate(root: Path) -> str:
    if (root/'specs/project2/v0.3.3/version_manifest.json').is_file():
        from project2_v033_report import generate as generate_v033
        return generate_v033(root)
    if (root / "specs/project2/v0.3.2/version_manifest.json").is_file():
        from project2_v032_report import generate as generate_v032
        return generate_v032(root)
    if (root / "specs/project2/v0.3.1/version_manifest.json").is_file():
        from project2_v031_report import generate as generate_v031
        return generate_v031(root)
    if (root / "specs/project2/v0.3/version_manifest.json").is_file():
        from project2_v03_report import generate as generate_v03
        return generate_v03(root)
    revision = revision_details(root)
    docs = root / "specs/project2" / revision["version"]
    audit = root / "audit/project2-v1"
    audit.mkdir(parents=True, exist_ok=True)
    progress_path = root / "specs/project2/progress.md"
    previous_progress = progress_path.read_text(encoding="utf-8") if progress_path.is_file() else ""
    # Preserve resume state rather than recreating the execution origin each run.
    state_path = audit / "execution_state.json"
    state = read_json(state_path)
    if state is None:
        state = {"started_at": datetime.now(timezone.utc).isoformat(), "base_commit": git_value(root, "rev-parse", "HEAD"), "branch": git_value(root, "branch", "--show-current")}
    frozen = enforce_frozen_documents(root, audit)
    with (docs / "traceability.csv").open(encoding="utf-8-sig", newline="") as handle:
        trace = list(csv.DictReader(handle))
    with (docs / "acceptance_scenarios.csv").open(encoding="utf-8-sig", newline="") as handle:
        scenarios = {row["scenario_id"]: row for row in csv.DictReader(handle)}
    runtime_path = audit / "traceability_runtime.json"
    runtime = read_json(runtime_path)
    if runtime is not None and runtime["source_sha256"] != sha256(docs / "traceability.csv"):
        raise ValueError("Runtime trace source hash differs; stop for version review")
    preflight = read_json(audit / "preflight_report.json") if revision["version"] == "v0.2" else read_json(audit / "spec_preflight.json")
    native, native_file = latest_native_gate(audit)
    gate_files = {"Chap12": "chap12_gate.json" if (audit/"chap12_gate.json").is_file() else native_file or "spec_preflight.json", "Chap13": "chap13_gate.json", "Chap14": "chap14_gate.json", "Chap15": "chap15_gate.json"}
    stages = []
    for name, filename in gate_files.items():
        report = read_json(audit / filename)
        stages.append({"stage": name, "status": stage_verdict(report), "system_gate_executed": bool(report and report.get("system_gate_executed")), "evidence_file": f"audit/project2-v1/{filename}" if report else None, "gate_scope": report.get("gate_scope") if report else None})
    failing_checks = [] if preflight is None else [check for check in preflight.get("scenario_checks", preflight.get("checks", [])) if check.get("consistency") == "冲突" or "actual_count" in check and (check.get("actual_count") != check.get("expected_count") or check.get("measurement_complete") is not True)]
    stop_reason = None
    if failing_checks:
        check = failing_checks[0]
        if "consistency" in check:
            stop_reason = f"数据预检冲突：{check['scenario_id']}；{check['reason']}。不得改动受保护规格。"
        elif check.get("measurement_complete"):
            stop_reason = f"冻结场景{check['scenario_id']}预期完整计数={check['expected_count']}，官方全文库独立复算={check['actual_count']}（谓词：{' AND '.join(check['predicate'])}）。规格与真实数据冲突；按硬约束停止，不改规格、查询、数据或测试。"
        else:
            stop_reason = f"规格前置检查未完成：{check.get('error', check.get('failure_kind', 'unknown'))}。停止，不伪造运行证据。"
    if native and stage_verdict(native) == "failed" and native["repair_rounds"] >= 2:
        failures = []
        for check in native["checks"]:
            if check["status"] == "passed":
                continue
            if isinstance(check["observed"], dict):
                actual = check["observed"]
                usage = check.get("result", {}).get("usage", {})
                workers = check.get("result", {}).get("workers", {})
                error = workers.get("rag", {}).get("error") or {}
                detail = f"；{usage.get('attempts')}次依赖后拦截新调用" if error.get("category") == "dependency_attempt_limit" else "；实际有引用回答，与预登记无答案状态冲突" if check["expected"]["worker_states"].startswith("RAG=no_data") and workers.get("rag", {}).get("evidence") else ""
                failures.append(f"{check['check']}：{actual['worker_states']}→{actual['overall']}{detail}")
            else:
                failures.append(f"{check['check']}：{check['observed']}")
        stop_reason = f"Chap12真实组合子门禁在{native['repair_rounds']}轮修复后仍失败；" + "；".join(failures) + "。达到修复上限，停止后续实现/评测，不改变预算、阈值、原问题或门禁。"
    components = component_evidence(audit)
    runtime_items = {item["requirement_id"]: item for item in (runtime or {}).get("items", [])}
    counts = Counter({"通过": 0, "部分": 0, "未完成": 0})
    runtime_rows = []
    for row in trace:
        existing = runtime_items.get(row["requirement_id"], {})
        evidence = existing.get("evidence_files", [])
        gates = existing.get("gate_stages", [])
        evidence_valid = bool(evidence) and all((root / name).is_file() for name in evidence)
        gates_valid = bool(gates) and all(any(stage["stage"] == name and stage["status"] == "passed" for stage in stages) for name in gates)
        # No system trace item is signed off solely by a diagnostic file or CSV.
        parts = [item for item in components if item["scenario_id"] in row["scenario_ids"].split(";")]
        status = existing.get("execution_status", "待实施") if evidence_valid and gates_valid else "部分" if parts else "待实施"
        counts["通过" if status == "通过" else "部分" if status == "部分" else "未完成"] += 1
        diagnostics = ["audit/project2-v1/spec_preflight.json"] if failing_checks and row["requirement_id"] in scenarios[failing_checks[0]["scenario_id"]]["requirement_ids"].split(";") else []
        runtime_rows.append({"requirement_id": row["requirement_id"], "source_status": row["status"], "execution_status": status, "actual": existing.get("actual", "未执行") if evidence_valid and gates_valid else "部分组件检查已执行，完整场景/阶段未通过" if parts else "未执行", "evidence_files": evidence if evidence_valid and gates_valid else sorted({p["evidence_file"] for p in parts}), "gate_stages": gates if evidence_valid and gates_valid else [], "partial_evidence": parts, "diagnostic_evidence_files": diagnostics})
    comparisons = []
    for name, relative in (
        ("原RAG / Agentic（冻结v0对照）", "evals/project2-v1/rag_vs_agentic/summary.json"),
        ("组合任务：单Agent / 固定Workflow / 新版本", "evals/project2-v1/ch12/summary.json"),
        ("可靠性改动前 / 后", "evals/project2-v1/ch15/summary.json"),
    ):
        data = read_json(root / relative)
        comparisons.append({"name": name, "status": "未执行" if data is None else data.get("status", "缺少程序结论"), "summary": data, "evidence_file": relative if data else None})
    heldout_calls = sum((read_json(audit / name) or {}).get("heldout_stage_calls_project2", 0) for name in gate_files.values())
    heldout_repetitions = sum((read_json(audit / name) or {}).get("heldout_repetitions_project2", 0) for name in gate_files.values())
    test_counts = junit_counts(audit / "native_gate_final.junit.xml") if native else junit_counts(audit / "spec_preflight.junit.xml")
    summary_tests = junit_counts(audit / "summary_v02.junit.xml") if revision["version"] == "v0.2" else junit_counts(audit / "summary.junit.xml")
    actions = (["决定下一轮实施授权及真实无答案场景的后续处理范围；本轮两次修复已用尽，不能自动换题/改门禁。"] if stop_reason and native else ["审批新的版本化规格以解决数据/预期冲突。"] if stop_reason else []) + [
        "git push / PR / 最终审阅：本范围禁止自动执行，由用户本人处理。",
        "第16章云账号、平台与预算：本范围之外，由用户本人提供并另行授权。",
        "向老师确认CL-03只读治理口径：当前按用户签署执行，不声称已获课程答复。",
    ]
    state.update({"active_spec_version": revision["version"], "current_stage": "Chap12" if stop_reason else next((s["stage"] for s in stages if s["status"] != "passed"), "scope_complete"), "execution_status": "stopped_gate_failure" if stop_reason and native else "stopped_specification_issue" if stop_reason else "awaiting_gates", "stop_reason": stop_reason, "repair_rounds": (native or {}).get("repair_rounds", 0), "heldout_stage_calls_project2": heldout_calls, "heldout_repetitions_project2": heldout_repetitions, "resume_progress_previously_present": bool(previous_progress), "updated_at": datetime.now(timezone.utc).isoformat()})
    native_checks = [x for x in (native or {}).get("checks", []) if "scenario_id" in x]
    conforming = sum(check["observed"] == check["expected"] and check["status"] == "passed" for check in native_checks)
    report = {"schema_version": 2, "generated_at": state["updated_at"], "branch": git_value(root, "branch", "--show-current"), "stages": stages, "traceability_counts": dict(counts), "traceability_total": len(trace), "comparisons": comparisons, "stop_reason": stop_reason, "heldout_stage_calls_project2": heldout_calls, "heldout_repetitions_project2": heldout_repetitions, "preflight_test_counts": test_counts, "summary_test_counts": summary_tests, "frozen_spec_files": len(frozen["files"]), "new_local_commits": int(git_value(root, "rev-list", "--count", f"{state['base_commit']}..HEAD")), "repair_rounds": state["repair_rounds"], "human_actions": actions, "baseline_source_integrity": read_json(audit / "baseline_source_integrity_final.json"),
              "spec_revision": revision, "preflight_status": (preflight or {}).get("status"), "component_tests": junit_counts(audit / "ch12_component_checks.junit.xml"), "batch_equivalence_tests": junit_counts(audit / "batched_retrieval.junit.xml"), "multiagent_regression": junit_counts(audit / "multiagent_regression.junit.xml"),
              "native_conformance": {"numerator": conforming, "denominator": len(native_checks), "wilson95": wilson(conforming, len(native_checks)), "repetitions": 1 if native_checks else 0, "conclusion": "仅描述，不作结论"}, "native_evidence_file": native_file}
    labels = {"passed": "通过", "failed": "失败", "not_executed": "未执行"}
    lines = ["# Project 2 自动执行汇总", "", f"**执行已停止。** {stop_reason}" if stop_reason else "完整阶段门禁尚未通过，不能宣布完成。", f"分支：`{report['branch']}`；来源：程序读取追踪表、JSON证据及JUnit。", "", "| 阶段 | 门禁结果 | 实际执行范围 |", "| --- | --- | --- |"]
    for stage in stages:
        scope = "真实组合子门禁；完整门禁/标定/对照未完成" if stage["gate_scope"] == "native_combination_subgate" else "规格前置检查；完整系统门禁未执行" if stage["gate_scope"] == "approved_specification_preflight" else "未开始" if stage["status"] == "not_executed" else "系统门禁"
        lines.append(f"| {stage['stage']} | {labels[stage['status']]} | {scope} |")
    lines.extend(["", f"追踪表：通过 **{counts['通过']}** / 部分 **{counts['部分']}** / 未完成 **{counts['未完成']}**（共{len(trace)}项；含范围外需求）。原表未改；执行状态另存runtime追踪。", "", "| 对照 | 关键结果（分子/分母、95%CI、退化项） |", "| --- | --- |"])
    for item in comparisons:
        result = "未执行；指标及退化项无实测数据，不记为零或‘不支持’" if item["summary"] is None else json.dumps(item["summary"], ensure_ascii=False, separators=(",", ":"))
        lines.append(f"| {item['name']} | {result} |")
    lines.extend(["", f"Project2 held-out累计：**{heldout_calls}**次阶段调用 / **{heldout_repetitions}**次重复；旧评测账本未改。"])
    lines.extend(["", "### 规格修订", "", f"v0.2数据修订 **{revision['delta_count']}处**；v0.1 **{len(frozen['files'])}份**批准工件未变。新版数据前提预检：{report['preflight_status']}（不证明RAG语义预期）；文档/哈希检查退出0。"])
    for change in revision["changes"]:
        old_values = '/'.join(str(x) for x in change['old_actual_count'])
        lines.append(f"- {change['scenario_id']}：原零值谓词实际{old_values} → 新谓词{' AND '.join(change['new_predicate'][0])}，独立计数{change['new_independent_count']}；状态/门禁不变。")
    conformance = report["native_conformance"]
    if conformance["denominator"]:
        ci = conformance["wilson95"]
        lines.append(f"\n最后一版组合门禁状态符合率：{conformance['numerator']}/{conformance['denominator']}，Wilson 95%CI [{ci[0]:.3f}, {ci[1]:.3f}]；单次、n<10，仅描述，不作结论；不是三重复对照成绩。")
    for label, key in (("组件检查", "component_tests"), ("批量查询等价性", "batch_equivalence_tests"), ("旧MultiAgent回归", "multiagent_regression")):
        item = report[key]
        if item:
            lines.append(f"{label}：{item['tests']}项，失败{item['failures']}，错误{item['errors']}。")
    if test_counts:
        lines.append(f"门禁pytest：{test_counts['tests']}项，失败{test_counts['failures']}，错误{test_counts['errors']}；修复轮数{report['repair_rounds']}。")
    if summary_tests:
        lines.append(f"汇总器检查：{summary_tests['tests']}项，失败{summary_tests['failures']}，错误{summary_tests['errors']}；契约测试(Mock)，不计系统验收。")
    if report["baseline_source_integrity"] and report["baseline_source_integrity"]["status"] == "passed":
        lines.append(f"冻结v0源码/配置：{report['baseline_source_integrity']['baseline_sut_files']}个文件哈希不变。")
    lines.extend([f"证据：[全项复算](<{(audit/'preflight_report.json').as_posix()}>) · [规格差异](<{(docs/'delta.md').as_posix()}>) · [最后门禁](<{(audit/(native_file or 'spec_preflight.json')).as_posix()}>)。分类：真实全文/FAISS/模型组合运行、契约测试(Mock)、DB故障注入；容器/云未执行。本地新增提交{report['new_local_commits']}（门禁未过，不提交）。", "", "需要本人处理：", ""])
    lines.extend(f"- {action}" for action in actions)
    markdown = "\n".join(lines) + "\n"
    (audit / "execution_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (audit / "traceability_runtime.json").write_text(json.dumps({"source": f"specs/project2/{revision['version']}/traceability.csv", "source_sha256": sha256(docs / "traceability.csv"), "items": runtime_rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (audit / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "specs/project2/summary.md").write_text(markdown, encoding="utf-8")
    progress = ["# Project 2 自动执行续跑记录", f"程序更新时间：{state['updated_at']}", f"当前阶段：{state['current_stage']}", f"执行状态：{state['execution_status']}", f"生效规格：{revision['version']}；新增数据谓词修订{revision['delta_count']}处；原v0.1不变", f"本地分支：{report['branch']}", f"基准提交：{state['base_commit']}", "已通过系统门禁：" + ("、".join(s['stage'] for s in stages if s['status'] == 'passed') or "无"), f"Project2 held-out累计阶段调用/重复：{heldout_calls}/{heldout_repetitions}", f"修复轮数：{state['repair_rounds']}（最多2；没有新授权不得再次执行原门禁轮次）", f"停止原因：{state['stop_reason'] or '完整门禁未执行'}", f"证据：audit/project2-v1/preflight_report.json；{native_file}；ch12_component_checks.junit.xml；native_gate_final.junit.xml；frozen_spec_snapshot.json；summary.json；traceability_runtime.json", "续跑先读本文件及execution_state.json；保留原0/1/2轮真实证据/登记/计数，不从头开始、不抬预算、不调阈值、不换问题。模型子进程已在TestClient关闭时终止；未启动持久API。", "当前Chap12部分组件已实施，两个真实组合子门禁未过；墙钟未标定/冻结、三重复对照和held-out未执行；Chap13/14/15未启动，Chap16及远端操作在范围外。"]
    progress_path.write_text("\n\n".join(progress) + "\n", encoding="utf-8")
    return markdown


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        text = generate(args.root.resolve())
    except (ValueError, KeyError, OSError, RuntimeError) as error:
        sys.stdout.write(f"FAIL summary generation: {error}\n")
        return 2
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
