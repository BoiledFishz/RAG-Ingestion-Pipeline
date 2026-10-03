# 2026-10-03 TechQA 定向整改

本轮处理明确包名被多余澄清、指令片段截断、来源操作/组件不匹配及校验重试信息不足。
代码版本 `3c7def2`；当前检索仍使用完整 801,996 篇官方 Technote、3,089,056 个 MiniLM
语义向量和相同 ID 的 BM25 索引，没有使用 Hash 替代 Dense，也没有新增合成知识库或问答。
模型为本机 Qwen2.5:7b，向量身份、模型摘要与 95 个运行源码文件哈希见
[环境快照](techqa_remediation_v4_environment.json)。

## 修改与边界

- Rewrite 识别带连字符/下划线的包名和版本；明确 API、错误码、包名及版本比较先检索。
  LLM 若多余澄清或改写了受保护标识，保留原始可检索问题。
- 900 字符的普通片段遇到指令引导句或列表边界时，可扩展至最多 1800 字符的原文指令组。
  完整列表超出上限时不截断发布，序列化 Context 仍受各服务的原有 Token 预算限制。
  处理安全公告中与表格连在同一行的通知页脚，保持引用为原文子串。
- 压缩前和发布前检查明确的安装/回滚前提、Socket Gateway/Probe 组件及同一产品的较旧
  最低版本错误前提。比较版本错误时要求两侧明确命名同一产品，不拿不同组件的版本相比。
  Critic 为这些冲突记录来源 ID、具体问题和替换建议。
- 校验重试包含具体失败字段与合法 ID；`trace.validation_failures` 保留第一次失败。
  修复上限仍是一次，最终失败继续拦截，不给失败结果拒答成功分。

这些是有限范围的显式规则和原文校验，不是完整的语义正确性证明；未知组件、隐含条件、
缺失步骤和错误的来源选择仍可能逃过检查。

## Enterprise 真实全库回归

16 条逐字复制的官方 dev 问题：4 条已知失败加原始顺序的 12 条其他问题，共 8 条 Y、8 条 N。
[来源核验](2026-10-03-remediation-source.json) 将问题、参考答案和 12 篇测试文档与官方原始文件
逐项比较。小型文档快照只供离线单元测试；真实运行检索全库，黄金答案不进入索引或 Agent。
这是开发回归，不是独立盲测。

| 相同 16 题 | 整改前归档版本 | 当前代码真实运行 |
|---|---:|---:|
| Y 正文 F1，要求正确文档引用 | 0.4295 | 0.4619 |
| Y 回答接受率 | 0.875 | 0.875 |
| N 标签拒答代理比例 | 0.250 | 0.125 |
| 多余/其他澄清次数 | 2 | 0 |
| 最终原文/结构校验失败 | 2 | 0 |
| 执行异常 | 0 | 0 |

完整记录见 [当前 16 题](../enterprise-ai-agent/evaluation/results/techqa_remediation_v4/runs.json)、
[运行配置](../enterprise-ai-agent/evaluation/results/techqa_remediation_v4/run_config.json) 与
[逐题对比](techqa_remediation_v4_comparison.json)。当前运行未续用旧答案。
N 标签只保证原始 DOC_IDS 内没有答案；全库可能检索到有效证据，不能把这个代理比例当成幻觉率。
比例本轮下降，不能声称拒答质量改善。F1 小幅上升也不能当成完整 310 题成绩提高。

| 案例 | 当前结果 | 尚未解决的部分 |
|---|---|---|
| DEV_Q000 安装 DASH 版本要求 | 拦截回滚文档和旧版本前提；返回无来源拒答 | 正确目标文档仍未进入 Top-10，问题没有得到解决 |
| DEV_Q007 Socket Gateway 包比较 | 实际检索并引用 swg21625776，排除 Probe 文档 | 正文 F1 仅 0.259，仍有无关标题、链接，完整选型说明需要改进 |
| DEV_Q113 WAS7 HTTPS | 首次错误记录为不存在的 source_claim；具体反馈重试后发布原文证据 | 原始标签为 N，不能计为拒答改善；事实完整性仍需核验 |
| DEV_Q236 API Connect 公告 | 通过原文校验并引用完整库中的 swg22006126 | 与原始候选范围不同，不能用回答接受替代人工正确性判断 |

`techqa_remediation_v1`、`v2` 保留修改中的完整 16 题及其已知错误；`v3` 在首题前中断，
有 interrupted.json，没有完整 summary，不能当作成功验收。

## Agent、Critic 与流程核验

四版本各运行同样的 15 条官方训练题，实际检索全库，共 60 次；执行错误 0。
Planner 重复 10 次，Schema/执行路径校验成功率 1.00，非法 Agent 0，计划形态 1 种。
[完整比较](../agentic-rag-homework/evaluation/results/techqa_remediation_v4/report.md) 与
[原始输出](../agentic-rag-homework/evaluation/results/techqa_remediation_v4/runs.json) 保留答案和 DAG 执行。

| 版本 | Y 正文 F1 | N 标签拒答代理比例 | LLM 调用 | Token 估算 | 平均延迟 ms |
|---|---:|---:|---:|---:|---:|
| Fixed | 0.2522 | 0.000 | 1.40 | 1918.9 | 8938 |
| ReAct | 0.2439 | 0.000 | 3.47 | 5579.5 | 14630 |
| Single | 0.2439 | 0.000 | 3.47 | 5632.2 | 12515 |
| Multi | 0.2081 | 0.333 | 6.60 | 8216.6 | 30862 |

旧版 Single/Multi Y 正文 F1 是 0.1891/0.1533，本轮有改善，但水平仍低。
Multi 的 N 标签代理比例仍是 0.333，其正文指标低于 Single，开销也更高；不能据此认为
Multi 一定优于 Single。严格 Failure Rate（正文 F1 未满分或异常）Single=1.00、Multi=0.9333，
这些不是崩溃率。Windows 共享桌面上的耗时不是隔离性能实验，旧 Fixed 延迟包含长时间阻塞，
不能把新旧耗时差全部归因于代码改进。
SPSS 题 Single 返回许可迁移片段、Multi 拒答；MQ 权限题引用其他文档，去掉文档 ID 门控的
正文 F1 仍约 0.166。代理评分有局限，但并不能把这些案例视为已经完整解决。

实际全库检索产生的固定证据上，Critic 对 15 题各重复两次，30 次均调用真实模型，跳过 0。
协议、充分性与最终诊断的一致性均为 1.00，模型错误 0，复核通过率 1.00；
通过率包含确认正确拒答，不等于有答案题回答正确。
Y 接受率仍为 0.50，Y 正文 F1 从 0.1665 降至 0.1406；N 标签代理比例仍为 0.3333。
首次复核通过率由 0.80 至 0.8667，平均重试由 0.20 至 0.1333，但质量没有证明改善。
本轮不能签收 Critic 的生产答案质量。见 [30 次结果](../agentic-rag-homework/evaluation/results/techqa_remediation_v4_critic/summary.json)。

[14 个真实模型 HTTP 流程](../evals/techqa_remediation_v4_api_smoke.json) 全部通过：
Dense/Sparse/Hybrid、空过滤拒答、Enterprise、RAG/Planner/ReAct/Single/Multi/Critic。
[三项目 pytest](techqa_remediation_v4_pytest.txt) 共 160 项通过（55 + 52 + 53）；
Ruff 通过，Mypy 分别检查 42/28/25 个源码文件通过。
另修复根项目 Mypy 的 `src` 发现路径，默认命令也可直接运行；保留一条不阻塞的 Starlette 弃用警告。
验收脚本最终退出 0；所有独立阶段均完成，没有将部分结果当成完整评测。

Windows PowerShell 5 在 `ErrorActionPreference=Stop` 下把重定向的普通 Python logging stderr
当作 NativeCommandError。本地控制试验复现退出 1；在捕获原生日志期间使用 Continue、
按原生退出码判断后退出 0。见 [脚本验证](2026-10-03-remediation-runner.json)。
修复不改变系统执行策略；每次默认使用新目录，也不覆盖历史结果。

## 复现与未完成项

```powershell
./scripts/start-local.ps1 -FullTechQA
python scripts/prepare_techqa_regression.py
./scripts/run-remediation-checks.ps1
```

脚本默认为结果生成时间戳名称；同名目录已存在时拒绝覆盖。完整 310 题新运行可指定
`enterprise-ai-agent/evaluation/results/techqa_semantic_v4`；本轮没有重跑该完整问答评测。
此前 310 题 F1=0.21303、N 代理比例=0.10 对应旧代码，仍保留在原目录。

仍需改进整体答案完整性、正确文档召回、人工核验的全库拒答与独立测试集质量。
全量 JSON 索引仍采用兼容旧 ID 的切片和官方标题摘要；没有把 300 多万个 Chunk 重新处理成
RCTS 与逐块 LLM 摘要。当前修复及流程通过均不能作为生产质量签收。
