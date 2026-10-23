"""Attribute every Multi-Agent result to the first layer where it went wrong (2026-10-20).

    python -m evaluation.chap12_trace_report RUN_DIR --split tune|sample

Reads RUN_DIR/traces.jsonl (written by chap12_eval --trace) and the split's gold file. Layers,
in pipeline order (the first one that loses the gold document is reported):
  L1 retrieval   gold document in neither the dense nor the sparse list, or cut by RRF fusion
                 (candidate_k 30)
  L2 rerank      in the fused candidates, but not among the top_k documents handed to the agent
  L3 context     handed to the agent, but not in the evidence the model saw (acceptance
                 threshold, conflict filters or token budget)
  L4 generation  in the evidence, but the model cited other documents or refused
  L5 supervisor  explanation correct, but withheld by the Supervisor or the data part is wrong
Unanswerable questions are correct only when refused; an answered one is reported as
"L4 refusal" together with the top returned score and its threshold.
Writes RUN_DIR/layer_attribution.json and RUN_DIR/layer_attribution.md. Diagnosis only:
nothing here selects a parameter.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SPLIT_DIRS = {"tune": HERE / "chap12/tune", "sample": HERE / "chap12"}
LABELS = {
    "correct": "正确",
    "failed": "运行失败或超时",
    "L1 retrieval: not retrieved": "L1 召回：稠密与稀疏都没检索到",
    "L1 retrieval: fusion cut": "L1 召回：融合后排在前 30 之外",
    "L2 rerank": "L2 重排：没进入交给模型的前 k 篇",
    "L3 context": "L3 上下文筛选：交给了 Agent，但没进入模型看到的证据",
    "L4 generation: cited other": "L4 生成：证据里有答案文档，但引用了别的文档",
    "L4 generation: refused": "L4 生成：证据里有答案文档，但模型拒答",
    "L4 refusal: answered unanswerable": "L4 拒答：不可回答题被作答",
    "L5 supervisor: withheld": "L5 Supervisor：答案被核验否决",
    "L5 supervisor: data": "L5 Supervisor / 数据：解释正确，但数据或产品错误",
}


def docs(items: list[dict[str, Any]] | None) -> list[str]:
    return [x["doc"] for x in items or []]


def attribute(row: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    s, layers = row["score"], row["layers"]
    retrieval, rag = layers.get("retrieval") or {}, layers.get("rag") or {}
    stages = retrieval.get("stages", {})
    out: dict[str, Any] = {"task_id": row["task_id"], "type": row["type"],
                           "answerable": s.get("answerable")}
    if s.get("correct"):
        return out | {"layer": "correct"}
    if not rag:
        return out | {"layer": "failed"}
    returned = retrieval.get("returned", [])
    top = returned[0] if returned else None
    out["top_returned"] = top
    if s.get("answerable") is False:
        if s.get("rag_correct"):
            return out | {"layer": "L5 supervisor: data"}
        return out | {"layer": "L4 refusal: answered unanswerable",
                      "evidence_docs": len(rag.get("evidence", []))}
    g = gold["document"]
    out["gold"] = g
    for name in ("dense", "sparse", "fusion", "rerank"):
        rank = next((x["rank"] for x in stages.get(name, []) if x["doc"] == g), None)
        out[f"rank_{name}"] = rank
    evidence, cited = docs(rag.get("evidence")), rag.get("cited", [])
    if out["rank_dense"] is None and out["rank_sparse"] is None:
        layer = "L1 retrieval: not retrieved"
    elif out["rank_fusion"] is None:
        layer = "L1 retrieval: fusion cut"
    elif g not in docs(returned):
        layer = "L2 rerank"
    elif g not in evidence:
        mine = next(x for x in returned if x["doc"] == g)
        out["gold_score"], out["gold_threshold"] = mine["score"], mine["threshold"]
        layer = "L3 context"
    elif g not in cited:
        layer = "L4 generation: cited other" if cited else "L4 generation: refused"
    elif not row.get("published"):
        layer = "L5 supervisor: withheld"
    else:
        layer = "L5 supervisor: data"
    return out | {"layer": layer}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--split", choices=sorted(SPLIT_DIRS), required=True)
    args = parser.parse_args()
    gold = {g["task_id"]: g for g in map(json.loads, (SPLIT_DIRS[args.split] / "mixed_gold.jsonl")
                                         .read_text("utf-8").splitlines())}
    rows = [json.loads(x) for x in (args.run / "traces.jsonl").read_text("utf-8-sig")
            .splitlines() if x.strip()]
    rows = [r for r in rows if r["system"] == "multi" and r["type"] in
            {"explain", "explain_and_data"}]
    items = [attribute(r, gold[r["task_id"]]) for r in rows]
    rewrites = Counter(bool((r["layers"].get("rag") or {}).get("rewrite_fallback"))
                       for r in rows)
    table: dict[str, dict[str, int]] = {}
    for it in items:
        group = "Y" if it["answerable"] else "N"
        table.setdefault(it["layer"], {"Y": 0, "N": 0})[group] += 1
    order = list(LABELS)
    report = {"run": str(args.run), "split": args.split, "tasks": len(items),
              "rewrite_fallback": {"yes": rewrites[True], "no": rewrites[False]},
              "by_layer": {k: table[k] for k in order if k in table}, "items": items,
              "method": __doc__.split("Layers,")[1].split("Writes")[0].strip()}
    (args.run / "layer_attribution.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    lines = [f"# 逐层归因（{args.split}，Multi-Agent，{len(items)} 题）", "",
             "| 层 | 可回答 | 不可回答 | 合计 |", "| --- | --- | --- | --- |"]
    for k in order:
        if k in table:
            y, n = table[k]["Y"], table[k]["N"]
            lines.append(f"| {LABELS[k]} | {y} | {n} | {y + n} |")
    lines += ["", f"查询改写回退到规则：{rewrites[True]} / {len(items)} 题。", ""]
    (args.run / "layer_attribution.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
