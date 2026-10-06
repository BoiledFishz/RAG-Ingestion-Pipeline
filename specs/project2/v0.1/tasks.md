# Project 2 分阶段任务 v0.1

编制日期：2026-10-05。状态：待用户实现前审阅，人工审阅日期未发生、待填写。**所有下列系统任务均待实施，所有验收未执行**。文件路径为预期证据位置，不代表文件已经存在。

证据分类只采用：真实运行、契约测试(Mock)、故障注入、未执行。一项需多类证据时分别保存来源与适用范围；本阶段只有文档编制/格式核对，不启动这些任务。需求逐项关联见 traceability.csv，具体场景见 acceptance_scenarios.csv。

| 任务 | 阶段与工作 | 验收条件 | 计划证据类型 | 预期证据文件（仓库相对路径） | 状态 |
| --- | --- | --- | --- | --- | --- |
| T00-01 | 实现前审阅 spec、plan、tasks 与 CL-01–08 | 日期、审阅人、决定及批准哈希真实记录；未决项不默认为批准 | 未执行 | audit/project2-v1/review.md | 待实施 |
| T12-01 | Chap12：版本化 Contract/入口与基线边界 | 新入口独立；旧 MultiAgentVersion 和 v0 行为不变；拒绝 oracle 字段 | 契约测试(Mock) | audit/project2-v1/contracts.json | 待实施 |
| T12-02 | 定义 TechQA 数据/规则版本与白名单 | 只用现有字段，QA sidecar 在线不可访问；manifest/schema/tokenizer 不符明确失败 | 契约测试(Mock)；真实运行 | audit/project2-v1/data_contract.json | 待实施 |
| T12-03 | 核心 DB Worker | 授权全集不同文档 COUNT/比较/交集，样本 limit 不影响计数，零/null 分开 | 真实运行；契约测试(Mock) | audit/project2-v1/db_worker.json | 待实施 |
| T12-04 | 验证核心能力独立性与必过项 | 无RAG/LLM仍运行；AC12-11比较/交集/部分计数和AC12-13候选不变性必过；独立全母体复算一致 | 真实运行；故障注入 | audit/project2-v1/worker_independence.json | 待实施 |
| T12-05 | 主体/资源/操作 Policy | 服务端范围不能被用户/Prompt/计划扩大；拒权零调用且无内容泄漏 | 契约测试(Mock)；真实运行 | audit/project2-v1/policy.json | 待实施 |
| T12-06 | API总Budget及tune标定 | 默认路由/异常/重试受临时90秒/16尝试/6LLM强制；按S08.1固定40题×3测量，不排除删失；审阅选值后冻结参数/报告/样本/配置SHA；内部可取消/计量 | 契约测试(Mock)；故障注入；真实运行 | audit/project2-v1/budget.json；evals/project2-v1/calibration/budget_frozen.json | 待实施 |
| T12-07 | RAG Adapter | 原 query/实际 query、Chunk/位置/排名保留；不降阈值/改提示词 A；空/错误/无引用分开 | 契约测试(Mock)；真实运行 | audit/project2-v1/rag_adapter.json | 待实施 |
| T12-08 | Supervisor/六状态汇合 | 36 对组合与全局覆盖规则；partial 显式缺口不算完成 | 契约测试(Mock) | audit/project2-v1/state_matrix.json | 待实施 |
| T12-09 | 真实组合任务及无答案挑战 | 使用已登记原query/操作；成功有独立数据与技术证据；AC12-23正常依赖下无适用技术证据而DB完成则partial；预期不成立保留失败不换题 | 真实运行 | audit/project2-v1/combined_run.json；audit/project2-v1/combined_no_answer_real.json | 待实施 |
| T12-10 | 固定任务单 Agent/流程对照 | 同输入/范围/版本，三重复与 CI，unsupported 不冒充成功；完整与 partial 分开 | 真实运行 | evals/project2-v1/ch12/summary.json | 待实施 |
| T12-11 | 新配置锁定与阶段末 held-out | 用户允许后一次阶段调用/三重复，累计次数入账；控制集/误接受/事实覆盖分列 | 真实运行 | evals/project2-v1/ch12/heldout_receipt.json | 待实施 |
| T12-12 | Chap12 工件/README/Diff/阶段 PR | 真实命令和结果、未覆盖项、经授权推送/PR 后审阅；未获授权只准备本地材料 | 未执行 | audit/project2-v1/ch12_submission.md | 待实施 |
| T13-01 | Chap13：Runtime 身份/State/TTL | owner/tenant/版本、节点所有权和状态迁移，24 小时 State 与访问策略 | 契约测试(Mock) | audit/project2-v1/runtime_contract.json | 待实施 |
| T13-02 | 尝试/节点结果持久化与恢复 | 实际停止/重启服务，同 run_id 恢复；跳过已完成节点、不重置预算 | 真实运行；故障注入 | audit/project2-v1/process_resume.json | 待实施 |
| T13-03 | 恢复拒绝/重复/不确定边界 | 未知/损坏/过期/越权/版本变更拒绝；并发 Resume 不重复昂贵调用；不确定尝试保留 | 契约测试(Mock)；故障注入 | audit/project2-v1/resume_edges.json | 待实施 |
| T13-04 | 只读治理及课程条件审批决定 | CL-03待向课程确认；只读白名单，未注册publish契约探针failed/failed；老师若要求Fake Publish，先改规格另审阅再隔离演示 | 未执行；契约测试(Mock) | audit/project2-v1/readonly_policy.md；audit/project2-v1/readonly_contract.json | 待实施 |
| T13-05 | 请求/节点/工具/恢复 Trace | 父子 Span、状态/时间/错误关联；一次真实失败可定位；访问、脱敏与保留验证 | 真实运行；契约测试(Mock)；故障注入 | audit/project2-v1/trace.jsonl | 待实施 |
| T13-06 | MCP/A2A 不采用决定及阶段提交 | 同进程边界有依据，不加协议凑数；阶段末评测与 PR 仍需另获授权 | 未执行 | audit/project2-v1/ch13_decisions.md | 待实施 |
| T14-01 | Chap14：真实服务 Dockerfile/Compose | 入口、依赖/Service Name、端口/健康语义正确；不复制 .venv 或人为拆 Worker | 真实运行 | audit/project2-v1/container_build.json | 待实施 |
| T14-02 | Secret/构建上下文/状态边界 | .dockerignore、Git/镜像不含 Secret；只读数据与可写 Runtime/保留卷分开 | 真实运行 | audit/project2-v1/container_boundaries.md | 待实施 |
| T14-03 | 干净容器主流程/日志/停止 | 原始 TechQA 组合请求经过真实 Worker；能诊断请求错误；停止不删保留卷 | 真实运行；故障注入 | audit/project2-v1/container_smoke.json | 待实施 |
| T14-04 | 容器 README/拓扑及阶段锁定 | 文档与真实配置一致；任何阶段末 held-out 新调用需先允许并登记 | 未执行 | audit/project2-v1/ch14_submission.md | 待实施 |
| T15-01 | Chap15：真实依赖故障设计/有界控制 | 可重试/不可重试、预算、DB 不重试、模型修复上限，未用机制理由 | 契约测试(Mock)；故障注入；真实运行 | audit/project2-v1/reliability.json | 待实施 |
| T15-02 | 既有 Cache 与重复 Resume 边界 | 返回前验权，模型/数据/文本版本可解释；无业务写操作，不伪造写幂等成绩 | 契约测试(Mock)；真实运行 | audit/project2-v1/cache_resume.json | 待实施 |
| T15-03 | 三重复前后性能/成本/诊断复测 | 同输入/权限/缓存/版本，均值范围 CI；一次真实诊断→单改→同条件复测 | 真实运行；故障注入 | evals/project2-v1/ch15/summary.json | 待实施 |
| T15-04 | 可靠性 README/阶段提交 | 配置/降级和限制清楚；锁定后 held-out 一次及 PR 均需用户允许 | 未执行 | audit/project2-v1/ch15_submission.md | 待实施 |
| T16-01 | Chap16：云平台执行前确认 | 用户授权、账号/区域/价格/资源边界已确认；本阶段不得操作 | 未执行 | audit/project2-v1/cloud_approval.md | 待实施 |
| T16-02 | 实际 Project 2 Endpoint/Secret/状态 | Health 与真实 TechQA 组合请求，Runtime Variables/监听/最小权限有证据 | 真实运行 | audit/project2-v1/cloud_endpoint.json | 待实施 |
| T16-03 | 云重启/重部署恢复 | 正确 owner/run_id、关键状态保留，临时状态限制不隐瞒 | 真实运行；故障注入 | audit/project2-v1/cloud_resume.json | 待实施 |
| T16-04 | Cloud Log/Trace 诊断及复测 | 非生产受控问题以非敏感 ID 关联；真实根因、修复及同条件复测 | 故障注入；真实运行 | audit/project2-v1/cloud_diagnosis.md | 待实施 |
| T16-05 | 停止资源/费用/限制和阶段提交 | 经授权停止并核对残留计费；部署步骤、结果、未覆盖项及 PR/Review 可追溯 | 真实运行 | audit/project2-v1/cloud_shutdown.md | 待实施 |

## 进入下一阶段的条件

本次仅登记50条查询侧任务（五层各8条、另10条无答案挑战）、42个场景和文档检查。CL-01/02/04/05/06/07已采纳草案；仍需用户确认CL-05选型、CL-08协议及CL-03课程答复。90/16/6只是标定前临时值；check_docs.py通过不关闭任何上表系统任务。

Chap12 先证明核心 Worker 和组合任务实际运行、权限/状态/预算符合规格，再推进服务 Runtime。Chap13 的实际恢复与 Trace 不用评测续跑代替。Chap14/15/16 分别收集容器、可靠性、云证据。每阶段完成后配置锁定，遵守阶段末 held-out 一次规则；本阶段不申请执行或自动跑任何评测。

如某条件项不采用，任务交付是经审阅的适用决定，不能写为对应功能已完成。人工批准、源码实现、真实运行和远端审阅是四个不同状态，均不能由本文件代填。
