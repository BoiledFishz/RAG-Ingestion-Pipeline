# Agent 实验报告

Provider: `ollama`；Model: `llama3.2:3b`；数据集 15 题；执行错误 0。

Answer Quality 是正文与官方参考答案的 Token F1，且要求引用正确文档；
来源引文与引用编号不参与得分。Failure Rate 是 F1 未满分或执行异常的比例，非崩溃率。
未知问题必须实际拒答；执行异常计为 0 分并保留。Token 为正则估算值。

| 指标 | Fixed | ReAct | Single | Multi |
|---|---:|---:|---:|---:|
| Answer Quality | 0.101 | 0.101 | 0.101 | 0.094 |
| Failure Rate | 0.933 | 0.933 | 0.933 | 0.933 |
| LLM Calls | 0.000 | 2.000 | 2.000 | 4.800 |
| Tool Calls | 3.000 | 2.000 | 2.000 | 2.067 |
| Token Usage | 0.000 | 1761.200 | 1758.933 | 4371.667 |
| Latency (ms) | 3487.669 | 3641.259 | 2688.858 | 9938.590 |
| Fallback cases | 0.000 | 0.000 | 0.000 | 3.000 |

Planner：10 次，Schema 成功率 100.0%，非法 Agent 输出比例 0.0%，计划形态 1 种。

逐题输出、错误、执行的 DAG 任务和 Critic 每轮问题保存在 runs.json。
Multi 按真实计划依赖分派任务；分析与报告节点是保留原文证据的确定性专家。
Critic 未通过时会明确记录 fallback，最终回答保留已有证据，不采用未验证诊断。

**Multi-Agent 不一定优于 Single Agent。** 专业分工可能改善复杂任务，但增加规划、交接和复核成本；必须把质量收益与调用、Token、延迟和失败率一起比较。

题目与参考答案来自官方 TechQA 训练集；15 题功能实验不等于全量开发集成绩。
