# v0.2 → v0.3 限定修订

授权日期2026-10-05；仅A预算与B状态/质量拆分。原v0.1/v0.2字节不变。

AC12-01的触发项为dependency_attempt_limit：16次依赖、2次LLM、19.184841秒，尚未触及6次LLM或90秒墙钟。证据：audit/project2-v1/native_gate_round2.json。
计数口径不改：实际SQL/commit/HTTP/推理边界预留，executemany逐实际语句；批量一个语句只计一次。没有缩小数字的重新定义。

| 文件/条目 | 旧值 | 新值与原因 | 证据 |
| --- | --- | --- | --- |
| spec.md / A_budget_protocol | 完整旧片段见delta.json | A_budget_protocol；用户A/B限定授权 | audit/project2-v1/native_gate_round2.json |
| spec.md / version_header | 完整旧片段见delta.json | version_header；用户A/B限定授权 | evals/project2-v1/calibration_v03/protocol.json |
| spec.md / B_state_vs_quality | 完整旧片段见delta.json | B_state_vs_quality；用户A/B限定授权 | evals/project2-v1/calibration_v03/protocol.json |
| tasks.md / A_budget_task | 完整旧片段见delta.json | A_budget_task；用户A/B限定授权 | audit/project2-v1/native_gate_round2.json |
| tasks.md / B_state_task | 完整旧片段见delta.json | B_state_task；用户A/B限定授权 | evals/project2-v1/calibration_v03/protocol.json |
| clarifications.md / A_CL08_measurement | 完整旧片段见delta.json | A_CL08_measurement；用户A/B限定授权 | audit/project2-v1/native_gate_round2.json |
| acceptance_scenarios.csv / AC12-01 | 完整旧片段见delta.json | A_budget_binding；用户A/B限定授权 | audit/project2-v1/native_gate_round2.json |
| acceptance_scenarios.csv / AC12-15 | 完整旧片段见delta.json | A_budget_binding；用户A/B限定授权 | audit/project2-v1/native_gate_round2.json |
| acceptance_scenarios.csv / AC12-16 | 完整旧片段见delta.json | A_budget_binding；用户A/B限定授权 | audit/project2-v1/native_gate_round2.json |
| acceptance_scenarios.csv / AC12-23 | 完整旧片段见delta.json | B_state_vs_quality；用户A/B限定授权 | evals/project2-v1/calibration_v03/protocol.json |

全部精确旧值/新值在delta.json保留。此时实测尚未结束；结果出现后只补实测值/冻结哈希，不凭候选值宣布完成。S07/场景集合/AC12-03/授权/范围/非目标/冻结协议/held-out规则不改。
