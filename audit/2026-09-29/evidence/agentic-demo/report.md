# 作业实验报告

## Fixed Research Workflow vs. ReAct Research Agent

| 指标 | Fixed | ReAct |
| --- | ---: | ---: |
| Answer Quality | 1.000 | 1.000 |
| Tool Calls | 3.00 | 1.20 |
| LLM Calls | 0.00 | 1.20 |
| Token Usage | 0.00 | 667.60 |
| Latency (ms) | 0.797 | 4.205 |

## Planner 稳定性（10 次）

- Structured Output 成功率：100%
- 非法 Agent 名称比例：0%
- Plan shape 数量：1

Agent 名称通过 `AgentName` 枚举限制；任务 ID、顺序和依赖由 Pydantic DAG 校验。

## Critic Loop

每轮保存 diagnosis、issues、suggestion 和 resolved_previous_issues。原始逐轮记录见
`runs.json` 的 `critic_attempt_log`；最多重试两次，即最多三轮 Diagnosis/Critic。

## Single Agent vs. Multi-Agent

| 指标 | Version A | Version B |
| --- | ---: | ---: |
| LLM Calls | 1.20 | 5.40 |
| Token Usage | 667.60 | 2035.40 |
| Latency (ms) | 2.818 | 13.632 |
| Answer Quality | 1.000 | 1.000 |
| Failure Rate | 0.000 | 0.000 |

## 结论

Multi-Agent 不一定优于 Single Agent。专业化分工和独立 Critic 对复杂、可分解任务有价值，
但 Planner、交接和复核会增加 LLM Calls、Token、延迟与新的失败点。简单问题通常由 Single
Agent 更经济地完成；只有质量收益大于协调成本时，Multi-Agent 才值得采用。

> 本表是 5 条合成问题上的离线可复现实验，不代表生产模型效果。Token 为正则估算值。
