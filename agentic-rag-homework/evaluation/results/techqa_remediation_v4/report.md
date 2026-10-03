# Agent 实验报告

Provider: `ollama`；Model: `qwen2.5:7b`；数据集 15 题；执行错误 0。

Answer Quality 是正文与官方参考答案的 Token F1，且要求引用正确文档；
sources 字段与引用编号不参与得分；正文中的逐字证据仍是实际回答。
Failure Rate 是 F1 未满分或执行异常的比例，非崩溃率。
未知问题必须实际拒答；执行异常计为 0 分并保留。Token 为正则估算值。

| 指标 | Fixed | ReAct | Single | Multi |
|---|---:|---:|---:|---:|
| Answer Quality | 0.202 | 0.195 | 0.195 | 0.233 |
| Answerable body F1 | 0.252 | 0.244 | 0.244 | 0.208 |
| Labelled N refusal | 0.000 | 0.000 | 0.000 | 0.333 |
| Failure Rate | 1.000 | 1.000 | 1.000 | 0.933 |
| LLM Calls | 1.400 | 3.467 | 3.467 | 6.600 |
| Tool Calls | 3.000 | 1.800 | 1.800 | 1.933 |
| Token Usage | 1918.867 | 5579.467 | 5632.200 | 8216.600 |
| Latency (ms) | 8938.244 | 14630.478 | 12514.542 | 30862.316 |
| Fallback cases | 0.000 | 0.000 | 0.000 | 0.000 |
| Critic rejected cases | 0.000 | 0.000 | 0.000 | 0.000 |

Planner：10 次，Schema 成功率 100.0%，非法 Agent 输出比例 0.0%，计划形态 1 种。

逐题输出、错误、执行的 DAG 任务和 Critic 每轮问题保存在 runs.json。
Multi 按真实计划依赖分派任务；分析与报告节点是保留原文证据的确定性专家。
Critic 未通过时明确记录 failed，返回复核失败，禁止发布被否决的诊断或先前答案。

**Multi-Agent 不一定优于 Single Agent。** 专业分工可能改善复杂任务，但增加规划、交接和复核成本；必须把质量收益与调用、Token、延迟和失败率一起比较。

题目与参考答案来自官方 TechQA 训练集；15 题功能实验不等于全量开发集成绩。
