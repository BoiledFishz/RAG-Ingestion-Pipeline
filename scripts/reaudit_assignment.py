"""Recheck the registered homework inventory against actual evidence only."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit/assignment-completion-20261007"


def read(name: str) -> dict[str, Any]:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def proof(name: str, kind: str) -> dict[str, str]:
    path = ROOT / name
    if not path.is_file():
        raise ValueError("Missing actual evidence: " + name)
    return {
        "file": name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "evidence_type": kind,
    }


def generate() -> dict[str, Any]:
    prefix = "audit/assignment-completion-20261007/"
    initial = read("audit/assignment-completion-20261007/requirements_audit.initial.json")
    tests = read(prefix + "final_tests/test_repair_round2/course_tests.json")
    if tests["status"] != "passed" or len(tests["projects"]) != 3:
        raise ValueError("Existing project test suites have not all passed")
    container = read(prefix + "container_gate_final/gate.json")
    required_container = {
        "clean_build",
        "ready_after_full_warmup",
        "real_combined_completed",
        "independent_count_exact",
        "input_fault_located_in_logs",
        "stop_retains_volume",
        "same_run_state_after_restart",
        "owner_isolation",
    }
    if {c["check"] for c in container["checks"]} != required_container or not all(
        c["observed"] is True for c in container["checks"]
    ):
        raise ValueError("Final-source real container gate not passed")
    reliability = read(prefix + "reliability_fault/gate.json")
    if reliability["status"] != "passed" or not all(c["observed"] for c in reliability["checks"]):
        raise ValueError("Required reliability fault checks not passed")
    before, after = (
        read(prefix + x + "/summary.json") for x in ("reliability_before", "reliability_after")
    )
    plans = [read(prefix + x + "/plan.json") for x in ("reliability_before", "reliability_after")]
    if plans[0]["tasks"] != plans[1]["tasks"]:
        raise ValueError("Reliability before/after task sets differ")
    if any(s["requests"] != 150 or s["repeats"] != 3 for s in (before, after)):
        raise ValueError("Reliability comparison incomplete")
    chap11 = read(prefix + "chap11/summary.corrected.json")
    if chap11["requests"] != len(read(prefix + "chap11/plan.json")["tasks"]) * 6:
        raise ValueError("Original RAG / Agentic comparison incomplete")
    for name in ("original_rag", "agentic_rag"):
        if chap11["systems"][name]["body_f1"]["denominator"] < 60:
            raise ValueError("Answerable question scoring missing")
        if chap11["systems"][name]["n_refusal"]["denominator"] < 30:
            raise ValueError("N question scoring missing")
    empty_case = read(prefix + "chap11/empty_retrieval.result.json")
    if empty_case["status"] != "passed" or not all(empty_case["checks"].values()):
        raise ValueError("Real empty-retrieval sample not passed")
    empty_timing = read(prefix + "chap11/empty_retrieval_timing.json")
    if not empty_timing["excluded_from_scored_set"]:
        raise ValueError("Supplementary censored timing must not enter comparison metrics")
    for name, digest in read("evals/protocol_v0/baseline_v0.config.json")["sut"]["files"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Frozen v0 changed: " + name)
    doc_output = (AUDIT / "docs_check.log").read_text(encoding="utf-8")
    if (
        "FAIL" in doc_output
        or not doc_output.strip()
        or not all(line.startswith("PASS") for line in doc_output.splitlines() if line.strip())
    ):
        raise ValueError("Approved document checker did not pass")
    completed_evidence = [
        proof(
            prefix + "final_tests/test_repair_round2/course_tests.json",
            "契约测试(Mock)/真实数据单元测试",
        ),
        proof(prefix + "docs_check.log", "真实运行（文档校验，非RAG实测）"),
    ]
    groups = {
        "RAG": [
            proof(prefix + "chap11/summary.corrected.json", "真实运行（调用分类更正；原记录保留）"),
            proof(prefix + "chap11/empty_retrieval.result.json", "故障注入"),
        ],
        "MA": [
            proof("audit/project2-v1/v031_chap12_gate.json", "真实运行/契约测试(Mock)/故障注入"),
            proof("audit/project2-course-completion-20261007/counts_v034.json", "真实运行"),
        ],
        "RT": [
            proof("audit/project2-v1/v033_chap13_gate.json", "真实运行/契约测试(Mock)/故障注入"),
            proof(prefix + "container_gate_final/gate.json", "真实运行/故障注入"),
        ],
        "ENV": [proof(prefix + "container_gate_final/gate.json", "真实运行/故障注入")],
        "REL": [
            proof(prefix + "reliability_fault/gate.json", "真实运行/故障注入"),
            proof(prefix + "reliability_before/summary.json", "真实运行"),
            proof(prefix + "reliability_after/summary.json", "真实运行"),
        ],
        "SDD": [
            proof("specs/project2/v0.1/approval_record.md", "真实运行（签署文件校验，非功能运行）")
        ],
    }
    missing = {"PRE-06", *(f"CLOUD-0{i}" for i in range(1, 6))}
    partial = {"PRE-01", "SUBMIT-01"}
    conditional = {"MA-08", "MA-09", "RT-06", "RT-07", "RT-10"}
    implementations = {
        "RAG": [
            "enterprise-ai-agent/agents/rag_agent/service.py",
            "enterprise-ai-agent/agents/rag_agent/rewrite.py",
            "enterprise-ai-agent/agents/rag_agent/compression.py",
            "enterprise-ai-agent/tools/techqa_retriever.py",
        ],
        "MA": [
            "enterprise-ai-agent/agents/project2/supervisor.py",
            "enterprise-ai-agent/tools/techqa_document_query.py",
            "enterprise-ai-agent/models/project2.py",
        ],
        "RT": [
            "enterprise-ai-agent/agents/project2/service_runtime.py",
            "enterprise-ai-agent/agents/project2/execution_clock.py",
            "enterprise-ai-agent/api/project2_runtime_main.py",
        ],
        "ENV": [
            "containers/project2/Dockerfile",
            "containers/project2/compose.yaml",
            ".dockerignore",
            "enterprise-ai-agent/api/project2_container_main.py",
        ],
        "REL": [
            "enterprise-ai-agent/agents/project2/cache_identity.py",
            "enterprise-ai-agent/agents/project2/batched_retrieval.py",
            "enterprise-ai-agent/agents/project2/budget.py",
            "enterprise-ai-agent/tools/techqa_document_query.py",
        ],
        "PRE": [
            "src/rag/generation/service.py",
            "enterprise-ai-agent/README.md",
            "enterprise-ai-agent/tools/techqa_document_query.py",
        ],
        "SDD": [
            "specs/project2/v0.1/approval_record.md",
            "specs/project2/v0.3.4/spec.md",
            "specs/project2/v0.3.4/tasks.md",
        ],
        "EVAL": ["scripts/run_assignment_comparisons.py", "scripts/project2_stage_eval.py"],
        "SUBMIT": ["enterprise-ai-agent/README.md"],
    }
    rows = []
    for item in initial["requirements"]:
        row = dict(item)
        rid = row["id"]
        row["spec_sections"] = row.pop("implementation", "")
        row["implementation"] = implementations.get(rid.split("-")[0], [])
        for name in row["implementation"]:
            if not (ROOT / name).is_file():
                raise ValueError("Missing implementation path: " + name)
        row["planned_evidence"] = row.pop("evidence", "")
        row["evidence"] = []
        if not row["assignment_required"]:
            row.update(status="➕", priority="P3", reason="保留约束/历史研究，暂停额外开发")
            if rid.startswith("HC-"):
                row["reason"] = "既有约束仍强制；不重复计入功能分，不取消约束"
                row["evidence"] = completed_evidence
        elif rid in missing:
            row.update(
                status="❌",
                priority="P0",
                reason="真实云部署及执行前平台确认未获授权，不能用本地/Mock替代",
            )
        elif rid in partial:
            row.update(
                status="⚠️",
                priority="P1",
                reason="本地实现、分支和运行材料已准备；远端Feature PR/Review仍禁止",
            )
            if rid == "PRE-01":
                row["reason"] += "；现有Ruff/mypy检查仍有失败，未宣称质量门禁通过"
                row["verification_requirement"] = (
                    "Chap12 HW验证方式及Chap13 HW验收：执行既有静态/类型/质量门禁"
                )
            row["evidence"] = completed_evidence
        else:
            row.update(
                status="✅", priority="P2", reason="实现及作业验证证据齐全；不声称答案达到生产质量"
            )
            row["evidence"] = completed_evidence + groups.get(rid.split("-")[0], [])
            if rid in conditional:
                row["reason"] = (
                    "条件性要求：批准范围未采用；不虚构实施，既有只读/顺序/本地策略已验证"
                )
                row["completion_basis"] = "documented conditional non-adoption"
            if rid.startswith("PRE"):
                row["evidence"] += groups["RAG"] + groups["MA"]
            if rid == "EVAL-02":
                row["evidence"] += groups["RAG"] + groups["REL"]
                row["evidence"].append(
                    proof(
                        "audit/project2-course-completion-20261007/historical_v033_summary.json",
                        "真实运行（既有组合对照聚合）",
                    )
                )
        rows.append(row)
    counts = Counter(r["status"] for r in rows if r["assignment_required"])
    if sum(counts.values()) != initial["required_count"]:
        raise ValueError("Requirement denominator mismatch")
    result = {
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": initial["scope"],
        "required_count": initial["required_count"],
        "counts": dict(counts),
        "requirements": rows,
        "source_audit_sha256": hashlib.sha256(
            (AUDIT / "requirements_audit.initial.json").read_bytes()
        ).hexdigest(),
        "heldout_new_calls": 0,
        "s14_status": "未通过",
        "scoring_status": "额外人工盲评待办；本轮不扩展",
        "all_assignment_complete": not any(
            r["assignment_required"] and r["priority"] in {"P0", "P1"} for r in rows
        ),
        "remaining": [
            r["id"] for r in rows if r["assignment_required"] and r["priority"] in {"P0", "P1"}
        ],
        "chap11": chap11,
        "supplementary_empty_retrieval_timing": empty_timing,
        "reliability_before": before,
        "reliability_after": after,
        "tests": tests,
        "static_checks": read(prefix + "final_quality/checks.json"),
        "stopped_for": (
            "明确禁止云部署/push/PR；既有静态检查未通过，已披露。"
            "不修改冻结代码、不转入额外优化"
        ),
    }
    (AUDIT / "requirements_audit.final.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# 作业逐条重新验收",
        "",
        f"必做覆盖：{counts['✅']}/{initial['required_count']}；部分{counts['⚠️']}；未完成{counts['❌']}。",
        "",
        "| ID | 状态 | 依据/限制 | 实际证据 |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['id']} | {row['status']} | {row['reason']} | "
            + "; ".join(p["file"] for p in row["evidence"])
            + " |"
        )
    (AUDIT / "requirements_audit.final.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def summary() -> str:
    """Generate the current one-page submission report from verified evidence."""
    from project2_v033_report import atomic_text

    report = generate()
    prior = read("audit/project2-course-completion-20261007/historical_v033_summary.json")
    docs = ROOT / "specs/project2/v0.3.4"
    approved = list(csv.DictReader((docs / "traceability.csv").open(encoding="utf-8-sig")))
    rows = report["requirements"]
    approved_ids = [row["requirement_id"] for row in approved]
    runtime_ids = [row["id"] for row in rows]
    if Counter(approved_ids) != Counter(runtime_ids):
        raise ValueError("Approved/runtime requirement ID counts differ")
    if any(row["status"] != "待实施" for row in approved):
        raise ValueError("Approved traceability status was changed")
    totals = {
        state: sum(row["status"] == state for row in rows) for state in ("✅", "⚠️", "❌", "➕")
    }
    if sum(totals.values()) != len(approved):
        raise ValueError("Runtime traceability denominator mismatch")
    table_check = {
        "status": "passed",
        "approved_rows": len(approved),
        "runtime_rows": len(rows),
        "approved_sha256": hashlib.sha256((docs / "traceability.csv").read_bytes()).hexdigest(),
        "requirement_ids_match": True,
        "approved_status_unchanged": True,
        "runtime_counts": totals,
    }
    (AUDIT / "two_table_consistency.final.json").write_text(
        json.dumps(table_check, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    def formatted(value: dict[str, Any]) -> str:
        if not value.get("denominator"):
            return "不可用"
        ci = "/".join(f"{v:.3f}" for v in value["ci95"])
        bounds = "/".join(f"{v:.3f}" for v in value["range"])
        result = (
            f"{value['mean']:.3f}（{value['numerator']:.2f}/{value['denominator']}；"
            f"CI95%[{ci}]；范围[{bounds}]）"
        )
        if value.get("independent_query_groups", value["denominator"]) < 10:
            result += "仅描述，不作结论"
        return result

    stages = []
    for chapter, name in (
        (12, "audit/project2-v1/v031_chap12_gate.json"),
        (13, "audit/project2-v1/v033_chap13_gate.json"),
        (14, "audit/assignment-completion-20261007/container_gate_final/gate.json"),
        (15, "audit/assignment-completion-20261007/reliability_fault/gate.json"),
    ):
        gate = read(name)
        passed = sum(
            c.get("observed") == c.get("expected") and c.get("status") == "passed"
            for c in gate["checks"]
        )
        stages.append(
            {
                "chapter": chapter,
                "passed": passed,
                "total": len(gate["checks"]),
                "status": "passed" if passed == len(gate["checks"]) else "failed",
                "evidence": proof(name, "真实运行/契约测试(Mock)/故障注入"),
            }
        )
    if any(stage["status"] != "passed" for stage in stages):
        raise ValueError("Engineering gate incomplete; do not publish a completion report")
    tests = report["tests"]["projects"]
    test_total = sum(p["totals"]["tests"] for p in tests)
    test_errors = sum(p["totals"]["failures"] + p["totals"]["errors"] for p in tests)
    if test_errors:
        raise ValueError("Test failures remain")
    ci_counts = report["counts"]
    lines = [
        "# 作业必做项验收汇总",
        "",
        f"范围：{report['scope']}。必做完成{ci_counts['✅']}/{report['required_count']}，"
        f"部分{ci_counts['⚠️']}，未完成{ci_counts['❌']}；未达到完整提交条件。",
        "",
        "| 阶段 | 实际工程门禁 | 限制 |",
        "| --- | --- | --- |",
    ]
    for stage in stages:
        limit = (
            "S14未通过，不能记完整通过"
            if stage["chapter"] == 12
            else "真实故障门禁；不声称性能改善"
            if stage["chapter"] == 15
            else "—"
        )
        lines.append(
            f"| Chap{stage['chapter']} | {stage['status']}；"
            f"{stage['passed']}/{stage['total']} | {limit} |"
        )
    docs_passes = len((AUDIT / "docs_check.log").read_text(encoding="utf-8").splitlines())
    frozen_count = len(read("evals/protocol_v0/baseline_v0.config.json")["sut"]["files"])
    lines.extend(
        [
            "",
            f"现有pytest：{test_total}项通过，失败/错误{test_errors}；"
            f"文档{docs_passes}项PASS；冻结v0的{frozen_count}个文件未改。",
            "静态检查："
            + "；".join(f"{x['name']} exit={x['exit_code']}" for x in report["static_checks"])
            + "。历史格式/类型问题保留，不把它们称为通过。",
            "",
            "| 对照（三重复，tune） | 结果 |",
            "| --- | --- |",
        ]
    )
    chap11 = report["chap11"]
    for system in ("original_rag", "agentic_rag"):
        metrics = chap11["systems"][system]
        lines.append(
            f"| {system} | R@5{formatted(metrics['retrieval_recall5'])}；"
            f"正文F1代理{formatted(metrics['body_f1'])}；"
            f"N拒答代理{formatted(metrics['n_refusal'])}；"
            f"LLM调用{formatted(metrics['llm_calls'])}；"
            f"秒{formatted(metrics['elapsed_seconds'])} |"
        )
    business = prior["business_tune"]
    unsupported = "；".join(
        f"{k}不支持{v['unsupported_numerator']}/{v['task_denominator']}"
        for k, v in business["legacy"].items()
    )
    lines.append(
        "| 单Agent / 固定Workflow / 新版本 | "
        + unsupported
        + "；新版本完整状态率"
        + formatted(business["metrics"]["complete"])
        + "。旧计数冲突保留，新DB复算不追溯改分 |"
    )
    for label, source in (
        ("可靠性前", report["reliability_before"]),
        ("可靠性后", report["reliability_after"]),
    ):
        metrics = source["metrics"]
        lines.append(
            f"| {label} | Worker失败{formatted(metrics['worker_failure'])}；"
            f"秒{formatted(metrics['elapsed_seconds'])}；"
            f"LLM调用{formatted(metrics['llm_calls'])} |"
        )
    declines = [x for x in chap11["answer_proxy_comparison"] if x["delta"] < 0]
    report["chap11_answer_proxy_declines"] = declines
    before_failure = report["reliability_before"]["metrics"]["worker_failure"]
    after_failure = report["reliability_after"]["metrics"]["worker_failure"]
    failure_delta = after_failure["numerator"] - before_failure["numerator"]
    lines.extend(
        [
            "",
            f"退化披露：Chap11正文F1代理下降{len(declines)}题（逐题见机器汇总）；"
            f"可靠性Worker失败多{failure_delta:g}次；"
            "增加集中于首轮冷缓存。未证明多智能体或可靠性改动性能更好。",
            "Token仅报告可观测值；原RAG生成Token未知，本机推理无虚构货币Cost。正文F1不是required_facts覆盖率。",
            "额外空检索示例实际拒答，但墙钟异常耗时"
            + f"{report['supplementary_empty_retrieval_timing']['elapsed_seconds']:.3f}秒；"
            "不纳入234次对照或正常延迟结论；原记录保留。",
            "",
            "**已知限制与评分**：S14未通过；原对照历史退化"
            + str(prior["old_quality"]["control_regressed_questions"])
            + "题/"
            + str(prior["old_quality"]["control_regressed_question_repeats"])
            + "题次；人工盲评待办，旧LLM评分不引用。completed不等于事实正确。",
        ]
    )
    n = prior["n_refusal_history"]
    lines.append(
        f"历史N拒答{n['numerator']}/{n['denominator']}，"
        f"95%CI{[round(v, 3) for v in n['cluster_bootstrap95']]}；本轮不宣称改善。"
    )
    states = ("completed", "partial", "no_data", "permission_denied", "timeout", "failed")
    for key, distribution in prior["state_distributions"].items():
        if (
            set(distribution["counts"]) != set(states)
            or sum(distribution["counts"].values()) != distribution["denominator"]
        ):
            raise ValueError("Historical state distribution inconsistent: " + key)
    lines.extend(
        [
            "**预算历史**：90（签署）→37.941（旧Chap12/失败恢复）→90（v0.3.3及本轮）；依赖19/LLM6不变，历史结果不混合。",
            f"**两表一致性**：{len(approved)}/{len(rows)}个ID匹配；批准表仍待实施。"
            f"运行表✅{totals['✅']} / ⚠️{totals['⚠️']} / ❌{totals['❌']} / ➕{totals['➕']}；"
            "各状态分布总数已由程序核对；非计分约束仍强制。",
            "**规格修订**：沿用批准v0.3.4；本轮规格修改0。v0.2/v0.3/v0.3.1/v0.3.2/v0.3.3修订、标定批次和哈希保留在历史聚合。",
            f"held-out累计{prior['heldout_stage_calls_project2']}次阶段/{prior['heldout_repetitions_project2']}次重复，本轮新增0；没有读取其答案用于设计。",
            "",
            "**停止原因与本人待办**：云部署/平台权限和费用确认、Feature PR/Review"
            "受现有禁止边界限制；需本人处理。CL-03仍待老师确认；Fake Publish未做。"
            "额外优化、调参、UI、重构和下一阶段任务已暂停。",
            "",
            "逐条实现与证据：audit/assignment-completion-20261007/requirements_audit.final.json；每条实际证据含SHA256。",
        ]
    )
    report["stages"] = stages
    report["two_table_consistency"] = table_check
    report["historical_aggregate_only"] = prior
    atomic_text(
        AUDIT / "summary.final.json", json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    markdown = "\n".join(lines) + "\n"
    atomic_text(ROOT / "specs/project2/summary.md", markdown)
    atomic_text(
        ROOT / "specs/project2/progress.md",
        "# 作业必做缺口续跑记录\n\n"
        + json.dumps(
            {
                "current_stage": "允许范围内作业验收结束",
                "execution_status": "stopped_at_authorization_boundary",
                "spec": "v0.3.4",
                "engineering_gates": stages,
                "assignment_counts": ci_counts,
                "required_count": report["required_count"],
                "remaining": report["remaining"],
                "s14_status": "未通过",
                "scoring_status": "待人工盲评；额外实验暂停",
                "heldout_stage_calls_project2": prior["heldout_stage_calls_project2"],
                "heldout_repetitions_project2": prior["heldout_repetitions_project2"],
                "new_heldout_calls": 0,
                "stop_reason": report["stopped_for"],
                "evidence": "audit/assignment-completion-20261007/summary.final.json",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    return markdown


if __name__ == "__main__":
    report = generate()
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "scope",
                    "required_count",
                    "counts",
                    "remaining",
                    "all_assignment_complete",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
