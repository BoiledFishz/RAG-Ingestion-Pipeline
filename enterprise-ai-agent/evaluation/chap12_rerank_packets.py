# ruff: noqa: E501  (the reference prompt is kept verbatim)
"""Before/after-rerank comparison packets for a manual ChatGPT check (2026-10-22, teacher's request).

    python -m evaluation.chap12_rerank_packets

From trace_tune (current configuration, Ollama 0.40.6), sample 10 answerable tasks (seed
20261022) whose top-5 documents differ between RRF fusion (before rerank) and the nomic rerank
(after). The fused candidates are rebuilt offline from the recorded retrieval query (BM25 + the
sample's MiniLM vectors, no model call) and must reproduce the traced fusion order; each document
is shown with its highest fused chunk. Writes rerank_packets/packets.md (paste-ready prompts:
group k-A = before rerank, k-B = after) and rerank_packets/answer_key.md (gold document and
answer, and where the gold document sits in A and B). Diagnosis only.
"""

from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path
from typing import Any

from rag.techqa.data import ROOT

HERE = Path(__file__).resolve().parent
TRACE = HERE / "results/chap12/trace_tune/traces.jsonl"
OUT = HERE / "results/chap12/rerank_packets"
SEED, N, TOP, CHARS = 20261022, 10, 5, 1200

PROMPT = """You are the final answerability judge and response generator.

User question:

{query}

Retrieved evidence chunks:

{chunks}

First, determine whether the retrieved chunks provide sufficient and direct evidence to answer the user's question.

Answerability requirements:

- The chunks must directly address the user's question, not merely discuss a similar topic.
- Product, component, version, platform, error code, vulnerability, and scenario details must match when relevant.
- The answer must be fully grounded in the provided chunks.
- Do not use general background knowledge to fill missing facts.
- Do not infer unsupported causes, compatibility claims, dates, remediation steps, or configuration values.
- A high retrieval score or keyword overlap is not sufficient evidence.
- If only part of the question is supported, answer only that part and explicitly identify the unsupported part.
- If the chunks are insufficient but a specific missing detail would make the question answerable, ask for clarification.
- If the chunks cannot support a reliable answer, refuse to provide a definitive answer.

Use exactly one decision: ANSWER, CLARIFY or ABSTAIN.
If ANSWER: answer only from the chunks and cite chunk IDs like [C1].

Return JSON: {{"decision": "...", "answer": "...", "citations": [...], "unsupported_aspects": [...]}}"""


def main() -> None:
    from agents.chap12.rag_worker import doc_id
    from tools.sample_retriever import SampleRetrieverTool

    tool = SampleRetrieverTool(ROOT / ".rag_data/chap12_tune.sqlite", rerank="lexical")
    tasks = {t["task_id"]: t for t in map(json.loads, (HERE / "chap12/tune/mixed_tasks.jsonl")
                                          .read_text("utf-8").splitlines())}
    gold = {g["task_id"]: g for g in map(json.loads, (HERE / "chap12/tune/mixed_gold.jsonl")
                                         .read_text("utf-8").splitlines())}
    rows = [json.loads(x) for x in TRACE.read_text("utf-8-sig").splitlines() if x.strip()]
    pool = []
    for r in rows:
        stages = (r["layers"].get("retrieval") or {}).get("stages", {})
        before = [x["doc"] for x in stages.get("fusion", [])][:TOP]
        after = [x["doc"] for x in stages.get("rerank", [])][:TOP]
        if r["score"].get("answerable") and before and after and set(before) != set(after):
            pool.append((r, before, after))
    picked = sorted(random.Random(SEED).sample(pool, N), key=lambda p: p[0]["task_id"])

    async def chunks(query: str) -> dict[str, Any]:
        stages: dict[str, Any] = {}
        await tool.pipeline.retrieve(query, mode=tool.mode, filters=tool.secure_filters({}),
                                     trace=stages)
        best: dict[str, Any] = {}
        for x in stages["fusion"]:
            best.setdefault(doc_id(str(x.metadata.get("parent_id", ""))), x)
        return best

    packets, key = ["# 重排前后对比（10 组，可直接粘贴到 ChatGPT）", "",
                    "每组两段：A = 重排前（融合顺序）前 5 条，B = 重排后前 5 条。分别新开对话粘贴，"
                    "比较两次的 decision 与答案。标准答案见 answer_key.md。", ""], \
        ["# 答案对照（不要粘贴给 ChatGPT）", "",
         "| 组 | 题号 | 答案文档 | 在 A 中的位置 | 在 B 中的位置 |", "| --- | --- | --- | --- | --- |"]
    details = []
    for n, (r, before, after) in enumerate(picked, 1):
        query = tasks[r["task_id"]]["query"]
        best = asyncio.run(chunks(r["layers"]["retrieval"]["query"]))
        traced = [x["doc"] for x in r["layers"]["retrieval"]["stages"]["fusion"]]
        if list(best)[:len(traced)] != traced:
            raise RuntimeError(f"{r['task_id']}: rebuilt fusion differs from the trace")
        g = gold[r["task_id"]]
        pos = {lab: (lst.index(g["document"]) + 1 if g["document"] in lst else "—")
               for lab, lst in (("A", before), ("B", after))}
        key.append(f"| {n} | {r['task_id']} | {g['document']} | {pos['A']} | {pos['B']} |")
        details += [f"## 第 {n} 组（{r['task_id']}）", "", "标准答案（节选）：", "",
                    "> " + " ".join(g["answer"].split())[:600], ""]
        for lab, lst in (("A（重排前）", before), ("B（重排后）", after)):
            body = "\n\n".join(
                f"[C{i}] {best[d].metadata.get('context_summary', '') or d}\n"
                f"{' '.join(best[d].text.split())[:CHARS]}" for i, d in enumerate(lst, 1))
            packets += [f"## 第 {n} 组 {lab}", "", "```text",
                        PROMPT.format(query=query.strip(), chunks=body), "```", ""]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "packets.md").write_text("\n".join(packets) + "\n", encoding="utf-8")
    (OUT / "answer_key.md").write_text("\n".join(key + [""] + details) + "\n", encoding="utf-8")
    print("\n".join(key))


if __name__ == "__main__":
    main()
