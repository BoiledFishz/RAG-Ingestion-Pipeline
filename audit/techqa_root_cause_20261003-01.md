# TechQA 五题根因实验（2026-10-03，Phase 1–2）

源码诊断提交 `5754e8f`。五题失败集与五题成功控制均使用原始官方问题、全库开放检索。
目标文档 ID 仅在检索完成后计分，未放进 query 或模型输入。
当前流水线的可选 trace 开/关，以及 Reranker 分量记录开/关，10题结果逐项完全相同。
原生全库排名、每个分量、5种权重×30/60/100候选×20/40重排及 Parent 组件记录见
`audit/techqa_root_cause_20261003-01/`。这些是开发实验，不是完整 dev 新成绩。

| 案例 | 已观察到的阶段 | 根因证据与排除项 | 置信度/最小下一步 |
|---|---|---|---|
| DEV_Q000 | Sparse Recall → Fusion → Rerank | BM25目标23，Dense Top100无目标；默认RRF30淘汰目标。60/100候选时融合46/47，当前重排仍不在Top40；60候选lexical+prior可进34。不是生成造成初次丢失 | 高；候选容量和重排同时是瓶颈。不能仅调权重或发布门槛，也不能直接推断更多候选全局更好 |
| DEV_Q007 | Evidence Extraction/Compression | 目标Dense/BM25/RRF/Rerank均1。Parent冻结；hint开关与limit1都返回开头发布/链接；limit2增加V8.1/V7.4规则，limit4增加操作系统/part number表。无需更换模型即可恢复原文候选 | 高；需按事实槽位选择两个互补片段，不能只增加limit而让首个噪声继续压制有效信息 |
| TRAIN_Q007 | Dense Recall → Fusion；Evidence/Critic | Dense目标18，BM25默认30无目标（Top100第41）；RRF30淘汰。100候选semantic-only重排15，当前39。正确Parent的旧passage仅考虑RESOLVING段，丢掉之前DIAGNOSING内的component-managed alias/wsadmin。旧真实Critic两次批准泛WAS迁移；本轮冻结正文重标中性ID的组件复查仍通过 | 高；融合容量、先验、解答区域及充分性均参与。提供互补原文后旧自由Critic拒绝，但要求未被证据支持的额外验证，不能视为可靠修复 |
| TRAIN_Q011 | Dense Recall/Rerank；Evidence；Evaluation Artifact | 目标Dense35、BM25Top100无目标。100候选当前rank30、semantic-only5、无prior7。冻结Parent limit2可提取Release25步骤。官方参考为Release20的sudo命令，和问题Release25不一致；不能修改参考抬分 | 高；候选/重排丢失与评分偏差同时存在。原问题正文已下载软件、已有activation code、请求新电脑许可，不能只凭标题把它归为纯installation并一概否定licensing回答 |
| TRAIN_Q006 | Evidence Extraction；Evaluation Artifact | 目标Sparse1、Fusion3、Rerank1；旧提取只返回affected versions/fix，limit4仍没有前面的VULNERABILITY DETAILS，因有RESOLUTION时只遍历后部区域。黄金短span主要描述漏洞，实际问题还问版本/细节 | 高；遍历完整相关章节并保留条件。F1不能独立衡量多方面覆盖 |

五个成功控制：DEV_Q002、010、012、TRAIN_Q000、001。默认目标最终排名3/1/1/1/1；
100候选semantic-only均排名1。只是这5题的检索不退化，不是全局检索无损证明。

Critic组件基线4次来自冻结的旧实际正文，以中性ID重标并使用实际source context：
TRAIN_Q007仅当前答案通过；加入正确文档的互补片段后自由Critic拒绝；TRAIN_Q011这次两种输入
都拒绝，与旧两次通过不同。重标/上下文和调用路径不同，因此这是组件对比，非旧轨迹精确回放。
原始输出保存在 `critic_baseline.json`。反复通过/拒绝与追问无证据的额外步骤表明必须显式验证
主请求事实和前轮issue，不能仅统计pass/一致性。

该 MQ 替代来源包含可行的一般身份配置建议，不能仅因其 DOC_ID 不同或 F1 为零就断言
其事实错误。本轮已确认的是它没有充分展示题目所述“已配置凭据但未使用”场景的具体配置，
以及原 Critic 没有逐事实或逐 issue 的显式证明。替代建议是否能解决具体 BPM 环境仍需独立核实。
原组件输入仅重标了 evidence ID，保留正文中的历史引用号；因此也不能把这些单独的 Critic 调用
当作通过完整 citation validation 的流水线结果。新 corruption benchmark 使用一致的中性引用。

阶段结论：没有证明模型更大即可解决；没有证明某种重排权重全局最优；没有改变默认排名。
下一步先补互补原文提取和逐issue修复核验，再参数化检索做固定集回归，最后冻结后完整复验。
