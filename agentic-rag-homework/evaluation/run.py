"""Reproducible comparisons with explicit providers and honest per-case failures."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import time
from collections import Counter
from collections.abc import Awaitable
from pathlib import Path
from typing import Any

from rag.techqa.data import question_text, questions

from agents.research import FixedResearchWorkflow
from agents.systems import MultiAgentVersion, SingleAgentVersion
from evaluation.factory import ROOT, build_advanced, build_rag, build_tools, model_from_env
from models.llm import MeteredModel
from models.schemas import AgentName, Metrics, RAGResponse, ResearchRun, SystemRun

LOGGER = logging.getLogger(__name__)


def quality(response: RAGResponse, item: dict[str, Any]) -> float:
    if not item["answerable"]:
        return float(
            not response.sources
            and response.confidence == 0
            and response.answer.startswith(
                (
                    "没有找到足够证据",
                    "知识库中没有足够信息",
                    "知识库无法回答",
                )
            )
        )
    # Source quotes and citation numbers are not an answer to the question.
    answer = re.sub(r"\[(?:S?\d+|evidence)\]", "", response.answer).casefold()
    if "ground_truth" in item:
        expected_tokens = Counter(re.findall(r"\w+", item["ground_truth"].casefold()))
        actual_tokens = Counter(re.findall(r"\w+", answer))
        common = sum((expected_tokens & actual_tokens).values())
        total = sum(expected_tokens.values()) + sum(actual_tokens.values())
        cited = any(s.document_id == item["expected_document"] for s in response.sources)
        return (2 * common / total if total else 0) * cited
    expected = item["expected"]
    return sum(
        bool(re.search(r"(?<!\w)" + re.escape(term.casefold()) + r"(?!\w)", answer))
        for term in expected
    ) / max(len(expected), 1)


async def observe(
    item: dict[str, Any],
    operation: Awaitable[ResearchRun | SystemRun],
    meter: MeteredModel | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        run = await operation
        return {
            "id": item["id"],
            "quality": quality(run.response, item),
            "run": run.model_dump(mode="json"),
            "metrics": run.metrics.model_dump(),
            "error": None,
        }
    except Exception as exc:
        LOGGER.exception("Evaluation failed for %s", item["id"])
        metrics = meter.snapshot() if meter else Metrics()
        metrics.latency_ms = (time.perf_counter() - started) * 1000
        return {
            "id": item["id"],
            "quality": 0.0,
            "run": None,
            "metrics": metrics.model_dump(),
            "error": type(exc).__name__,
        }


def aggregate(version: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = max(len(rows), 1)

    def average(key: str) -> float:
        return sum(row["metrics"][key] for row in rows) / count

    return {
        "version": version,
        "llm_calls": average("llm_calls"),
        "tool_calls": average("tool_calls"),
        "token_usage": average("input_tokens") + average("output_tokens"),
        "latency_ms": average("latency_ms"),
        "answer_quality": sum(row["quality"] for row in rows) / count,
        "failure_rate": sum(bool(row["error"]) or row["quality"] < 1 for row in rows) / count,
        "error_count": sum(bool(row["error"]) for row in rows),
        "fallback_count": sum(
            any(task["status"] == "fallback" for task in (row["run"] or {}).get("executions", []))
            for row in rows
        ),
    }


async def evaluate(provider: str | None = None, planner_runs: int = 10) -> dict[str, Any]:
    selected = provider or os.getenv("MODEL_PROVIDER", "ollama")
    dataset = [
        {
            "id": r["QUESTION_ID"],
            "query": question_text(r),
            "answerable": r["ANSWERABLE"] == "Y",
            "ground_truth": r["ANSWER"],
            "expected_document": r["DOCUMENT"],
        }
        for r in questions("fixture")
    ]
    comparisons: dict[str, list[dict[str, Any]]] = {
        "fixed": [],
        "react": [],
        "single": [],
        "multi": [],
    }
    for item in dataset:
        rag, search, documents = build_tools()
        comparisons["fixed"].append(
            await observe(
                item,
                FixedResearchWorkflow(rag, search, documents).run(item["query"]),
            )
        )
        for version in ["react", "single", "multi"]:
            meter, planner, research, critic = build_advanced(model_from_env(selected))
            if version == "multi":
                operation = MultiAgentVersion(planner, research, critic, meter).run(item["query"])
            elif version == "single":
                operation = SingleAgentVersion(research).run(item["query"])
            else:
                operation = research.run(item["query"])
            comparisons[version].append(await observe(item, operation, meter))
            LOGGER.info(
                "%s %s quality=%.2f error=%s",
                version,
                item["id"],
                comparisons[version][-1]["quality"],
                comparisons[version][-1]["error"],
            )

    stability = []
    invalid_names = total_outputs = 0
    for index in range(planner_runs):
        meter, planner, _, _ = build_advanced(model_from_env(selected))
        try:
            plan = await planner.run(dataset[0]["query"])
            record = {"run": index + 1, "plan": plan.model_dump(mode="json"), "error": None}
        except Exception as exc:
            record = {"run": index + 1, "plan": None, "error": type(exc).__name__}
        for raw in meter.outputs:
            total_outputs += 1
            try:
                tasks = json.loads(raw).get("tasks", [])
                invalid_names += any(t.get("agent") not in set(AgentName) for t in tasks)
            except (ValueError, AttributeError, TypeError):
                pass  # Parse/schema failures are reported by valid_schema_rate, not name validity.
        record["metrics"] = meter.metrics.model_dump()
        record["raw_outputs"] = meter.outputs
        stability.append(record)
    valid_plans = [row["plan"] for row in stability if not row["error"]]
    shapes = {
        tuple((task["agent"], tuple(task["dependencies"])) for task in plan["tasks"])
        for plan in valid_plans
    }
    rag_cases = []
    for category, query in [
        ("answerable", dataset[0]["query"]),
        ("ambiguous", "help"),
        ("unanswerable", next(item["query"] for item in dataset if not item["answerable"])),
    ]:
        rag_cases.append(
            {
                "category": category,
                "query": query,
                "response": (await build_rag().run(query)).model_dump(),
            }
        )
    summaries = {name: aggregate(name, rows) for name, rows in comparisons.items()}
    return {
        "methodology": {
            "provider": selected,
            "model": os.getenv("OLLAMA_MODEL", "llama3.2:3b") if selected == "ollama" else "demo",
            "dataset_size": len(dataset),
            "planner_runs": planner_runs,
            "token_count": "regex estimate of prompts and outputs, not provider billing tokens",
            "quality": "official answer token F1 in answer body, with correct document citation",
            "failure": "answer quality below 1 or execution error; errors score zero",
            "tools": "shared official TechQA full corpus: Qdrant + BM25 + bounded nomic reranking",
            "specialists": "LLM research/diagnosis/critic; deterministic analyst/report writer",
        },
        "rag_three_categories": rag_cases,
        "planner_stability": {
            "runs": planner_runs,
            "valid_schema_rate": len(valid_plans) / max(planner_runs, 1),
            "invalid_agent_rate": invalid_names / max(total_outputs, 1),
            "unique_plan_shapes": len(shapes),
            "observations": stability,
        },
        "fixed_vs_react": {"fixed": summaries["fixed"], "react": summaries["react"]},
        "single_vs_multi": [summaries["single"], summaries["multi"]],
        "observations": comparisons,
        "critic_attempt_log": [
            attempt
            for row in comparisons["multi"]
            if row["run"] and row["run"].get("critic")
            for attempt in row["run"]["critic"]["attempts"]
        ],
        "error_count": sum(value["error_count"] for value in summaries.values())
        + sum(bool(row["error"]) for row in stability),
    }


def markdown(result: dict[str, Any]) -> str:
    method = result["methodology"]
    fixed, react = result["fixed_vs_react"]["fixed"], result["fixed_vs_react"]["react"]
    single, multi = result["single_vs_multi"]
    lines = [
        "# Agent 实验报告",
        "",
        f"Provider: `{method['provider']}`；Model: `{method['model']}`；"
        f"数据集 {method['dataset_size']} 题；执行错误 {result['error_count']}。",
        "",
        "Answer Quality 是正文与官方参考答案的 Token F1，且要求引用正确文档；",
        "来源引文与引用编号不参与得分。Failure Rate 是 F1 未满分或执行异常的比例，非崩溃率。",
        "未知问题必须实际拒答；执行异常计为 0 分并保留。Token 为正则估算值。",
        "",
        "| 指标 | Fixed | ReAct | Single | Multi |",
        "|---|---:|---:|---:|---:|",
    ]
    for label, key in [
        ("Answer Quality", "answer_quality"),
        ("Failure Rate", "failure_rate"),
        ("LLM Calls", "llm_calls"),
        ("Tool Calls", "tool_calls"),
        ("Token Usage", "token_usage"),
        ("Latency (ms)", "latency_ms"),
        ("Fallback cases", "fallback_count"),
    ]:
        values = " | ".join(f"{row[key]:.3f}" for row in [fixed, react, single, multi])
        lines.append(f"| {label} | {values} |")
    stability = result["planner_stability"]
    lines += [
        "",
        f"Planner：{stability['runs']} 次，Schema 成功率 "
        f"{stability['valid_schema_rate']:.1%}，非法 Agent 输出比例 "
        f"{stability['invalid_agent_rate']:.1%}，"
        f"计划形态 {stability['unique_plan_shapes']} 种。",
        "",
        "逐题输出、错误、执行的 DAG 任务和 Critic 每轮问题保存在 runs.json。",
        "Multi 按真实计划依赖分派任务；分析与报告节点是保留原文证据的确定性专家。",
        "Critic 未通过时会明确记录 fallback，最终回答保留已有证据，不采用未验证诊断。",
        "",
        "**Multi-Agent 不一定优于 Single Agent。** 专业分工可能改善复杂任务，"
        "但增加规划、交接和复核成本；必须把质量收益与调用、Token、延迟和失败率一起比较。",
        "",
        "题目与参考答案来自官方 TechQA 训练集；15 题功能实验不等于全量开发集成绩。",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/results")
    parser.add_argument("--provider", choices=["demo", "ollama"], default=None)
    parser.add_argument("--planner-runs", type=int, default=10)
    args = parser.parse_args()
    if args.planner_runs < 1:
        parser.error("--planner-runs must be positive")
    result = asyncio.run(evaluate(args.provider, args.planner_runs))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "runs.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output / "report.md").write_text(markdown(result), encoding="utf-8")
    LOGGER.info("Report written to %s, errors=%d", args.output, result["error_count"])
    return int(result["error_count"] > 0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    raise SystemExit(main())
