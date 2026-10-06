# Project 2 自动执行汇总

程序状态：**stopped_s14_acceptance**。批准S14未满足：tune原成功对照7题退化；80份答案仍缺独立双评分。工程门禁通过，质量未验收；本阶段held-out已消费一次，不改配置重跑，不把阶段记为完整通过或推进Chap13。
分支 `codex/project2-ch12`；held-out累计 **1次阶段调用 / 3次重复**。

| 阶段 | 完整门禁 |
| --- | --- |
| Chap12 | 通过 |
| Chap13 | 未执行 |
| Chap14 | 未执行 |
| Chap15 | 未执行 |

追踪：通过 **0** / 部分 **23** / 未完成 **38**；没有完整门禁证据的项不记通过。

| 三类对照 | 关键结果 / CI / 退化项 |
| --- | --- |
| 原RAG / Agentic | 未执行；没有实测结论 |
| 单Agent / 固定Workflow / 新版本 | complete=129/150；均值0.86，范围[0.86, 0.86]，95%CI [0.738, 0.93]；partial=15/150；均值0.1，范围[0.1, 0.1]，95%CI [0.043, 0.214]；count_exact=150/150；均值1，范围[1, 1]，95%CI [0.929, 1]；elapsed_seconds=1876.752/150；均值12.512，范围[11.185, 14.92]，95%CI [11.168, 13.822]；single_agent不支持=150/150，未启动模型，不作成本优势比较；fixed_workflow不支持=150/150，未启动模型，不作成本优势比较；未完整完成21项；完整明细见summary.json |
| 可靠性改动前 / 后 | 未执行；没有实测结论 |

### 标定批次

| 批次 | 槽位记录 | 状态 | 删失原因 | 用于决策 |
| --- | --- | --- | --- | --- |
| 1 | 300/300 | incomplete_censored | 用户记录的主机睡眠删失；P2-PLATFORM-01/combination/第3次/2098.058秒 | 否 |
| 2 | 300/300 | selected | 无已记录删失 | 是 |
批次1：因主机睡眠删失，未用于决策；原文件/哈希不变。不同批次不混合、不平均、不剔除单条。
所选批次2；冻结硬上限：依赖19 / LLM 6 / 墙钟37.941秒。
[三重复均值/范围、分子/分母与95%CI](<C:/Users/zacha/Documents/Ingestion Pipeline/evals/project2-v1/calibration_v031/batch2/metrics_ci.json>)。
N拒答质量（非门禁）：56/549，按题聚类95%CI [0.06060606060606061, 0.14652014652014653]；三重复均值/范围 0.10200364298724955/[0.09836065573770492, 0.1092896174863388]。冻结v0结论不变，不宣称质量提升。
真实组合子门禁：passed；未通过项：无。
当前真实组合子门禁第1轮：555/555，失败观察0；未完成不能判通过。

### 规格修订

v0.3.1仅新增S08.2操作性段落（1处精确插入、4项授权操作）；采用16/6调用下限。S08.1、32/12熔断、S07、场景/门禁/held-out及其余CL决定不变；旧三版和批次1保持。
文档检查11行PASS；manifest SHA256：`80455fc850af285c0c4af7998f2ead9061b9b13e649037bd64bebe931971df28`。

修订记录：v0.2 2处（原零值假设与官方全文库复算冲突；按用户限定授权替换数据谓词，状态和门禁不变:2）；v0.3 10处（A_budget_protocol:1, version_header:1, B_state_vs_quality:2, A_budget_task:1, B_state_task:1, A_CL08_measurement:1, A_budget_binding:3）；v0.3.1 1处（authorized_operational_insertion:1）

### 两表一致性

程序比对 **passed**：批准表61行、运行表61行；ID无缺失/新增/重复，批准状态与执行状态分开。冻结v0的65份源码/配置哈希不变。
证据：[文档输出](<C:/Users/zacha/Documents/Ingestion Pipeline/audit/project2-v1/docs_check_v031.log>) · [批次协议](<C:/Users/zacha/Documents/Ingestion Pipeline/evals/project2-v1/calibration_v031/protocol.json>) · [两表比对](<C:/Users/zacha/Documents/Ingestion Pipeline/audit/project2-v1/v031_traceability_comparison.json>)。新增本地提交3。

需要本人处理：

- 若程序报告授权范围外问题或两轮仍失败，决定后续授权；不放宽门禁。
- git push / PR / 最终审阅由本人处理；第16章云账号与预算另行授权。
- 向老师确认CL-03；Fake Publish未实施。
