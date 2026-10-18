"""Render the comparison tables in specs/chap12-supervisor/comparison.md from result files.

    python -m evaluation.chap12_report > ../specs/chap12-supervisor/_tables.md
Every number printed here is read from a JSON file under evaluation/ (paths are printed)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RUNS = {"评测集（sample，种子 20261011）": HERE / "results/chap12/offline_v3_sample_rotated",
        "确认集（confirm，种子 20261013，冻结配置 2f7fe55 只运行一次）":
            HERE / "results/chap12/offline_v3_confirm_once"}
LABEL = {"p1_single": "Project 1 原配置", "single": "单 Agent（当前 RAG）",
         "multi": "Multi-Agent"}


def f(m: Any, digits: int = 3) -> str:
    if not isinstance(m, dict) or m.get("mean") is None:
        return "—"
    ci = m.get("ci95")
    return f"{m['mean']:.{digits}f} [{ci[0]:.2f}, {ci[1]:.2f}]" if ci else f"{m['mean']:.3f}"


def table(path: Path) -> str:
    data = json.loads((path / "summary.json").read_text("utf-8"))["systems"]
    lines = [f"来源：`{path.relative_to(HERE.parent).as_posix()}/summary.json`", "",
             "| 类型 | 系统 | 正确完成 | 整体完成* | RAG 正确 | Y 接受 | N 拒答 | BA | Y 引用金标 "
             "| Y token F1 | R@1 / R@8 / MRR | 数据正确 | 产品一致† | 相关文档含金标 "
             "| 延迟 mean/p95 ms | LLM 调用 | SQL 语句 |",
             "| --- " * 17 + "|"]
    for kind in ("explain", "explain_and_data", "data", "all"):
        for system in ("p1_single", "single", "multi"):
            b = data[system].get(kind)
            if b is None:
                continue
            r = b.get("retrieval_y")
            retr = f"{r['R@1']:.3f} / {r['R@8']:.3f} / {r['MRR']:.3f}" if r else "—"
            lat = b["latency_ms"]
            lines.append(
                f"| {kind} (n={b['tasks']}) | {LABEL[system]} | {f(b['correct_completion'])} | "
                f"{f(b['complete_rate (status=completed; includes wrong N publications)'])} | "
                f"{f(b.get('rag_correct'))} | {f(b.get('y_accept'))} | {f(b.get('n_refuse'))} | "
                f"{f(b.get('balanced_accuracy'))} | {f(b.get('y_gold_cited'))} | "
                f"{f(b.get('y_token_f1'))} | {retr} | {f(b.get('data_correct'))} | "
                f"{f(b.get('product_matches_gold_doc'))} | "
                f"{f(b.get('related_docs_contain_gold'))} | "
                f"{lat['mean']:.0f} / {lat['p95']:.0f} | {b['llm_calls_mean']} | "
                f"{b['sql_mean']:.1f} |")
    return "\n".join(lines)


REAL = {"评测集（sample，每类 30 题 × 3 次重复）": HERE / "results/chap12/ollama_run1",
        "确认集 confirm2（种子 20261014，每类 30 题，只运行一次）":
            HERE / "results/chap12/ollama_run1_confirm2_once"}


def real_table(path: Path) -> str:
    """Real-profile table: adds tokens, embedding calls and failure rate."""
    data = json.loads((path / "summary.json").read_text("utf-8"))["systems"]
    lines = [f"来源：`{path.relative_to(HERE.parent).as_posix()}/summary.json`", "",
             "| 类型 | 系统 | 正确完成 | BA | Y 接受 | N 拒答 | Y 引用金标 | R@8 | 数据正确 "
             "| 产品一致† | 相关文档含金标 | 延迟 mean/p95 ms | LLM 调用 "
             "| prompt / completion token | embedding 调用 | 失败率 |",
             "| --- " * 16 + "|"]
    for kind in ("explain", "explain_and_data", "data", "all"):
        for system in ("p1_single", "single", "multi"):
            b = data[system].get(kind)
            if b is None:
                continue
            r = b.get("retrieval_y")
            lat = b["latency_ms"]
            pt, ct = b["prompt_tokens_mean"], b["completion_tokens_mean"]
            tok = f"{pt:.0f} / {ct:.0f}" if pt is not None else "—（未调用模型）"
            lines.append(
                f"| {kind} (n={b['tasks']}) | {LABEL[system]} | {f(b['correct_completion'])} | "
                f"{f(b.get('balanced_accuracy'))} | {f(b.get('y_accept'))} | "
                f"{f(b.get('n_refuse'))} | {f(b.get('y_gold_cited'))} | "
                f"{r['R@8']:.3f} | " if r else
                f"| {kind} (n={b['tasks']}) | {LABEL[system]} | {f(b['correct_completion'])} | "
                f"{f(b.get('balanced_accuracy'))} | {f(b.get('y_accept'))} | "
                f"{f(b.get('n_refuse'))} | {f(b.get('y_gold_cited'))} | — | ")
            lines[-1] += (
                f"{f(b.get('data_correct'))} | {f(b.get('product_matches_gold_doc'))} | "
                f"{f(b.get('related_docs_contain_gold'))} | {lat['mean']:.0f} / {lat['p95']:.0f} | "
                f"{b['llm_calls_mean']:.2f} | {tok} | {b['embedding_calls_mean']:.2f} | "
                f"{f(b['failure_rate (failed+timeout)'])} |")
    return "\n".join(lines)


def curve() -> str:
    path = HERE / "chap12/tune/refusal_signals.json"
    rows = json.loads(path.read_text("utf-8"))["top1_rerank_score"]["curve"]
    step = max(1, len(rows) // 12)
    picked = rows[::step]
    chosen = min(rows, key=lambda r: abs(r["threshold"] - 0.5404))
    if chosen not in picked:
        picked.append(chosen)
    picked.sort(key=lambda r: r["threshold"])
    out = [f"来源：`{path.relative_to(HERE.parent).as_posix()}`（调参集，hybrid + MiniLM 重排，"
           f"top-1 分数 ≥ 阈值即接受；共 {len(rows)} 个阈值点，下表等距抽取，"
           "并加入采用值 0.5404 附近的点）", "",
           "| 阈值 | Y 接受率 | N 拒答率 | BA |", "| --- | --- | --- | --- |"]
    for r in picked:
        mark = " ← 采用值附近" if r is chosen else ""
        out.append(f"| {r['threshold']:.4f}{mark} | {r['y_accept']:.3f} | {r['n_refuse']:.3f} | "
                   f"{r['ba']:.3f} |")
    return "\n".join(out)


def main() -> None:
    import sys

    if "--real" in sys.argv:
        for title, path in REAL.items():
            print(f"### {title}\n\n{real_table(path)}\n")
        return
    for title, path in RUNS.items():
        print(f"### {title}\n\n{table(path)}\n")
    print("### 调参集 top-1 重排分数阈值曲线\n\n" + curve() + "\n")
    decomposition = json.loads((HERE / "chap12/results/v1_v2_failed_decomposition.json")
                               .read_text("utf-8"))
    print("### v1 → v2 failed 44 → 0 的拆分\n\n来源：`evaluation/chap12/results/"
          "v1_v2_failed_decomposition.json`\n")
    for cause, count in decomposition["causes"].items():
        print(f"- {cause}: {count}")


if __name__ == "__main__":
    main()
