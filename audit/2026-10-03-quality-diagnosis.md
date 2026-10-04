# TechQA 回答质量整改与实验验收

结论：当前默认十题链路可以运行，已知Critic组件缺陷检测得到改善；回答完整性、误拒和修复稳定性
仍未通过生产质量门槛。新完整复验、独立人工评分与Ingestion A/B收益均未冒填成绩。

本报告区分源码/运行事实、根因假设、作业缺口、生产质量问题和评测局限。
所有业务问题和知识文档来自原始 IBM TechQA。错误命令、删步骤等仅是保存原文的
Critic 组件腐败试验；没有替换官方问题、答案、DOC_IDS 或 Y/N 标签。

## 根因与五题分析

阶段诊断与 Parent 冻结实验见 [根因报告](techqa_root_cause_20261003-01.md)。
原始查询/归档 Rewrite、每层 Top100 候选、目标 rank、Reranker 分量和消融均保存于
[诊断目录](techqa_root_cause_20261003-01/manifest.json)。目标 ID 只用于检索后评分。

| 题目 | 已确认的故障阶段 | 直接证据 | 置信度与排除项 |
|---|---|---|---|
| DEV_Q000 | Dense Recall、Fusion、Rerank；候选错误回答的 Generation | Dense Top100 无目标，BM25 为23；RRF30丢失，60/100时为46/47；所有候选消融仍未进入最终5。原文查询补丁级别被错误当作升级解决方案 | 高：初次丢失发生在生成前；提高接受率不能修复召回 |
| DEV_Q007 | Evidence Extraction、Compression、Generation/Critic | 正确 Parent 在全部阶段第1；旧 limit1 只有发布/下载信息，互补片段恢复 V8.1/V7.4 与 OS/part number。审核又将 Message Bus 的通用表当作指定 Socket 包比较 | 高：冻结 Parent 排除了检索故障；恢复候选信息不等于比较答案已完整 |
| TRAIN_Q006 | Evidence Extraction、Evaluation Artifact | RESOLUTION 限定丢掉前部漏洞描述；新片段保留 CVE、描述、4.1.1/4.2.0、Huawei 条件、APAR/修复。旧短 reference 只覆盖漏洞描述 | 高：提取位置已直接验证；F1 单独不能量化所有事实覆盖 |
| TRAIN_Q007 | Dense/Sparse Recall、Fusion/Rerank、Evidence、Critic | Dense18、BM25Top100为41；默认融合淘汰。DIAGNOSING 内 component-managed alias/wsadmin 曾被丢弃；通用 WAS/Maximo 相关文档被审核认可 | 高：融合容量与提取均有直接证据。通用 WAS 建议是否可行不能仅按 DOC_ID 断言；Maximo 片段不针对已配置身份被替代的主请求 |
| TRAIN_Q011 | Dense Recall、Rerank、Evidence、Critic、Evaluation Artifact | Dense35；100候选当前重排30、semantic-only5。冻结 Parent 可提取 Release25；官方参考含 Release20命令；许可查询被当作代码应用 | 高：本文不修改参考答案。原正文已下载、已有代码，licensing 并非天然错误，但代码查询不能代替应用步骤 |

没有证据表明更大模型、Cross-encoder 或 Multi-Agent 必然修复这些问题。
消融为开发集10题，不是盲测；默认 0.50/0.30/0.20 和30/20/5仍未改动。
源码 trace 开/关的10题检索输出逐项相同，仅支持诊断没有改变这一集合的排序。

## 代码修改

| 文件/函数 | 修改前 → 修改后 | 目的与回归风险 |
|---|---|---|
| `src/rag/retrieval/pipeline.py`、`TechQAReranker.rerank` | 无逐层记录 → 可选 trace、分量记录 | 定位丢失层；不改变排序 |
| `src/rag/techqa/evidence.py:aspect_passages` | 单一解答区域/一个 passage → 全相关章节、至多两个互补原文跨度 | 保留版本条件、步骤、比较规则；跨度变大可能挤占 token budget |
| `src/rag/techqa/facts.py` | 无主请求事实槽位 → query-derived 比较/安全公告/凭据/激活/步骤槽位 | 无 QA ID/gold hard-code；模式分类和模型判断仍会误判 |
| 两个 Agent 的 compressor | Parent 单片段 → 两个互补跨度，保留来源/边界/覆盖提示 | 提取覆盖改善；提示不是事实充分性的证明 |
| `agentic-rag-homework/agents/critic.py:verify_issues` | 下一轮整体 pass 清掉全部问题 → 每 issue 的实际答案和证据证明 | 修复无法被隐式批准；审核模型可能误判修复或误拒 |
| `src/rag/techqa/retrieval.py:RerankWeights` | 固定公式 → 校验过的可配置权重，默认保持 | 消融无需改源码；新权重须重新校准阈值、完整评估后才能采用 |
| `src/rag/techqa/claims.py` | 只选择原文 → 可选 claims/source 绑定生成、literal/command 校验、逐 claim 与主请求审核 | 支持 partial、阻止若干无来源建议；同模型审核仍有误批/误拒，不能作为事实证书 |
| Enterprise `LLMSelector`、Agentic `GroundedAnswerer` | 首个有限候选组被认可即结束 → 可选同文档审核、后续文档/partial 候选 | 减少不同文档条件混淆；增加调用量，可能使模型认可另一篇相关但不适用的文档 |
| `agents/research.py:LLMResearchPolicy` | ReAct只观察旧limit1 → 有预算的两个互补观察片段 | 最终 generation/critic 仍须验证答案；不能以 finish 或高分替代充分性 |
| `src/rag/techqa/protocol.py`、各评测入口 | 可覆写目录/部分配置指纹 → 拒绝覆写、源码/数据/模型摘要/参数记录 | 不续用变更源码的 checkpoint；旧历史记录未回写补造新字段 |

实现提交顺序：`5754e8f` 诊断；`e3c0809` 互补证据；`6a11e74` 逐事实/逐 issue；
`2a464fe` 重排参数化。后续受控生成与复现保护单独提交。
后续提交为`0582605`受控回答/复现保护、`2112845`累计Critic问题及修复证明、
`1fda5bb`隔离Ingestion试验；最终默认入口实验使用`1fda5bb`源码。

## 最小原生实验

Qwen2.5:7b；完整801,996文档/3,089,056 MiniLM向量及同ID BM25。使用五个失败题和
DEV_Q002/010/012、TRAIN_Q000/001 五个原成功对照。各实验为独立新目录，未续用旧答案。
10题均为Y，不能从这个集合估计 N refusal proxy；旧 summary 中无N的0只是历史实现返回值。

| 相同10题 | R@5 | R@10 | MRR | 正文F1×正确文档门控 | 有来源回答比例 | 平均延迟ms |
|---|---:|---:|---:|---:|---:|---:|
| 03：受控生成+claim/事实审核 | .700 | .700 | .6333 | .1068 | .400 | 64199 |
| 04：原文提取+事实审核 | .700 | .700 | .6333 | .3431 | .600 | 27756 |
| 05：同文档原文提取+事实审核 | .700 | .700 | .6333 | .4375 | .900 | 28759 |
| 06：主请求/比较实体/命令/步骤审核 | .700 | .700 | .6333 | .4188 | .600 | 75074 |
| 07：最终源码默认extractive、事实审核关闭 | .700 | .700 | .6333 | .4381 | .800 | 20799 |

三轮都执行完成且无执行异常；03仍有6个最终校验拒绝，不能把异常为0当作回答成功。
05接收率/F1较高，同时误接受了 DASH 查询补丁级别、Maximo 连接配置、Portal其他问题的
配置片段。它没有通过事实适用性验收。01/02为有 interrupted.json 的中断试验，无完整成绩。

[06完整十题](../enterprise-ai-agent/evaluation/results/techqa_quality_pilot_20261003-06/summary.json)
未复用checkpoint，执行异常为0，运行前后源码/归档/阈值/索引manifest摘要相同。
DEV_Q000、DEV_Q007、TRAIN_Q007拒答，TRAIN_Q006保留全部公告事实。
TRAIN_Q011仍是较笼统的许可说明，没有Release25 Mac的具体操作，不能因自动审核标记complete
就视为完整。五个原成功对照中四个回答，DEV_Q002误拒；DEV_Q010恢复正确Oracle字符集来源。
正文仍有断开的URL、空bullet和命令换行噪声。已知误答受到遏制，同时接受率下降、延迟显著上升；
阶段门槛仍失败。此表是不同代码的小集开发实验，延迟来自共享Windows主机，不是隔离性能压测。
06在最后的版本表条件守卫之前运行，该守卫另有组件实验，未将06成绩补记为修改后成绩。
06及随后Critic04的136个Python文件保存在
[可核验源码快照](techqa_source_snapshots_20261003-01/manifest.json)。06通过撤销其后仅新增的条件守卫
重构，聚合SHA256与原运行记录逐字节一致；Critic04直接复制当轮未变化的源码。
这些是实验留档，不是通过Phase5生产冻结。03/04/05没有完整源码字节快照，本文保留其哈希和结果，
但不宣称能仅凭当前Git HEAD精确重现它们。

[07默认入口完整十题](../enterprise-ai-agent/evaluation/results/techqa_quality_pilot_20261003-07_default/summary.json)
使用最终提交源码，执行异常0，前后源码和关键数据摘要一致。P8恢复回答，Oracle字符集题却拒答，
五个成功对照仍只回答四个。Socket只返回V8.1部分；MQ返回诊断跟踪/错误码说明，没有解释配置的
身份为何被替换；SPSS仍缺具体操作。这些正文均可逐题查看，不能凭引用合法或较高接受率验收。
默认路径耗时较少，同时少了实验审核的若干完整性保障；两条路径当前均不能用于生产质量结论。
Critic05/Enterprise07的完整源码也已加入同一快照目录，其聚合摘要与两次协议一致。

[冻结证据回放](techqa_selection_replay_20261003-01/summary.json)10题也完整结束，源码未在运行中改变；
操作审核拦截 DASH 错误回答，却误批 Message Bus 版本表，并使原成功对照发生拒答/校验退化。
回放没有新检索成绩，也没有 RAGAgent 整条重试路径，不能冒充全链路回归。

因此受控生成仍只在 `TECHQA_GENERATION=controlled` 时开启；模型事实/同文档审核仅在
`TECHQA_FACT_AUDIT=1` 时开启，默认保留提取路径。没有因本轮低分而调低拒答门槛。
后续代码又增加了比较实体的实际正文约束：别的包的通用版本表不能证明指定选项；
这个确定性修复有保存的真实失败单元测试，尚不能代替新原生全链路验收。

首轮 [Critic 十例×三版本](../agentic-rag-homework/evaluation/results/techqa_critic_components_20261003-01/summary.json)
完整30次，源/模型/配置协议在运行前后相同。初次判定的组件标签是工程/AI辅助标注，非人工黄金集。

| 版本 | defect recall | false accept | false reject | Critic/修复平均调用 | Token估算 | 增量延迟ms | 有协议错误的案例 |
|---|---:|---:|---:|---:|---:|---:|---:|
| No Critic | .000 | 1.000 | .000 | 0.0 | 0 | 0 | 0 |
| Legacy Critic | .625 | .375 | .000 | 2.9 | 3181.3 | 25854 | 5 |
| Fact/issue Critic，尚无完整性守卫 | .375 | .625 | .000 | 3.3 | 3921.7 | 42337 | 1 |

这个新版比旧版漏检更多，不能作为质量改善。No Critic 的0调用/0延迟是接受注入答案的增量对照，
不是完整RAG零调用；其余两版使用相同的受控修复器。8个缺陷、2个正确对照，一次重复不足证明稳定。
标题单独视图的installation案例有主请求歧义，其标签只是组件工程假设，不能当作官方Y/N真值。
`issue_repair_rate`、`new_issue_rate` 和 `final_fact_coverage` 暂为null；Critic自己pass不替代独立事实判定。

随后仅补两类有来源依据的确定性守卫：实际命令必须保留引用源中的参数；已复制的编号步骤
不能遗漏尾部步骤。共享setup后的编号重启按分支处理，不要求用户执行全部替代方案，也不把
自由paraphrase强制改成逐字引用。版本条件和一般语义缺陷仍需独立判断。

[第二轮完整十例](../agentic-rag-homework/evaluation/results/techqa_critic_components_20261003-02/summary.json)
仅重跑新版，使用同一案例集：defect recall=.875、false accept=.125，
但 false reject=.500（两个正确对照中误拒一个），平均6.4次调用、8131.5估算token、
84917ms，3个案例出现协议错误。缺失Huawei适用条件仍被放行；合理的证据不足拒答被误拒。
提高缺陷检出率的同时增加了误拒和成本，这一版仍不能通过生产验收。

随后增加实际正文的symptom/required_steps守卫，并进行
[两例针对性复验](../agentic-rag-homework/evaluation/results/techqa_critic_components_20261003-03/summary.json)：
只保留symptom的错误回答被拒绝，证据不足时的合理拒答被接受。
该子集的defect recall=1、false accept=0、false reject=0，各分母仅为1；
平均4次调用、6222.5估算token、57873ms，1个案例出现协议错误。
它只能证明这两个保存案例的本次表现，不能与上一轮其他八例拼成当前源码的完整十例成绩。
三轮均保存每次issue和修复轨迹，运行前后协议摘要一致；02/03另外保存原始模型输出。
01只有解析后的运行轨迹，未补造当时没有记录的原始输出。

[04完整十例](../agentic-rag-homework/evaluation/results/techqa_critic_components_20261003-04/summary.json)
加入限定在受影响版本表中的逐行条件守卫：本次8/8缺陷被初次拦截，2/2正确对照被接受，
defect recall=1、false accept=0、false reject=0；初次判断无协议错误。
平均6.9调用、9054.5估算token、87272ms，修复过程中4个案例出现协议/校验错误。
这只是同一开发组件集的一次重复，标签依然是工程标注；它支持已知缺陷检测改善，
没有证明陌生问题泛化、修复事实正确性或稳定性。8个缺陷案例最终Critic均未通过，
最终判定不替代独立事实审查，修复三个指标继续为null。

04的删条件案例第二轮还出现明确误标：实际正文仍缺一个版本的条件，却把
`Missing required fact: affected_versions` 标成resolved。后续另加修复证明守卫：
仍缺的事实、未完整的复制步骤和版本行条件不能被无关但逐字匹配的quote清除。
另一个驱动漏洞是第二轮新问题会替换未解决的首轮问题。
[修改前故障探针](techqa_issue_history_probe_20261003-01.json)使用真实来源删条件正文和Critic替身，
第三轮错误通过；[修改后同路径](techqa_issue_history_probe_20261003-02.json)保留两个累计问题并拒绝通过。
这两个是确定性故障路径验证，不是原生模型成绩。测试同时验证确有修复证明的旧问题能正常移除。

[05两例原生复验](../agentic-rag-homework/evaluation/results/techqa_critic_components_20261003-05/summary.json)
使用累计问题及修复证明守卫的新源码：删条件、改相邻版本均初次拒绝，
第三轮继续验证首轮事实issue与第二轮协议issue，未再把删条件标成已修复。
检出2/2、误接受0/2；没有正确对照，false reject为null。
两个修复过程仍有协议/校验错误，均耗尽两次重试，平均7调用、8488估算token、97436ms。
该实验支持跨轮问题保留和已知误标修复，不能补成当前源码的完整十例稳定性成绩。

## 事实评分和指标局限

[CVE三种答案比较](techqa_factual_review_20261003-01/cve_slot_comparison.json)保留原答案、官方短参考、
目标文档派生答案及AI辅助的五项0/1/2槽位评分。旧实际正文保留版本和修复却缺漏洞描述；
官方短参考相反。这个实验展示 F1 与请求覆盖的差异，不改变官方评分定义。

[人工审核表](techqa_factual_review_20261003-01/human_review_worksheet.json)保存10题正文、原始证据和
六项0/1/2字段。`human_factual_metric` 均未评分；AI/工程师代理读到的判断不会冒称独立人工。
[AI辅助逐题审阅](techqa_factual_review_20261003-01/ai_assisted_review.json)与官方指标分开保存六项评分和理由；
它没有独立人工审核身份，也不替代最终验收。
新人工审核、最终修复的事实评分仍为 Not yet verified。
[06逐题AI审阅与未评分人工表](techqa_factual_review_20261003-02/ai_assisted_review.json)
使用同样六项0/1/2字段，记录四个未回答题和SPSS/展示缺口；官方指标保持原值。
N仅是原DOC_IDS内无标注答案，全库可能有有效文档；N refusal proxy不是幻觉率。

## Ingestion范围

已准备独立2,000文档闭库样本：只按SHA256(document_id)抽样，未按题目/答案/标签选择。
legacy=8,718 chunk，RCTS=8,982 chunk。源样本SHA256为
`21717365b87193df15d7768838295f97f57108d8e61003b655d574f2d424d248`。
[真实摘要启动试验](techqa_ingestion_pilot_20261003-02/startup_metrics.json)对最先待处理的20个RCTS块
实际调用Llama3.2:3b，失败0，平均1442ms、中位1121ms，总成功调用28835ms；包含首次模型加载。
摘要、chunk hash、原文和模型摘要均已保存。这20块不是随机质量抽检，不能据此估计全库准确率。
8,736个唯一hash中仅完成20个，hash缓存可继续，但摘要阶段尚不完整。
这不等于已经完成 RCTS+LLM-summary A/B；B索引、召回/事实覆盖收益尚未验证，A/B评测阶段尚未实现。
全量索引没有覆盖或重建；完整库仍为legacy chunk+official title summary。

## 源码与可复现检查

当前根项目81、Enterprise52、Agentic59项pytest均通过，共192项。
三个项目分别运行，避免同名api/models/agents包互相污染；Ruff和Mypy检查通过。
这些只支持代码/故障路径运行，不证明语义事实正确。当前Starlette/httpx兼容性弃用警告仍存在。
根项目检查45个源文件，Enterprise26、Agentic26；未因该警告修改依赖或历史指标。

## 完整复验与验收门槛

Phase4没有证明“原成功无明显退化”和“没有增加误接受”，因此按照本轮严格实施顺序，
不进入生产参数冻结和 dev310/Agent60/Critic30 新全量复验。旧成绩保留，但不填写为新成绩。
三阶段标签已通过 GitHub 远端只读核验，均存在；其历史指向没有移动。
本轮只核验旧标签存在及SHA，没有在旧标签重新运行，独立运行复验为Not yet verified。

| 验收项目 | 当前判断 | 依据 |
|---|---|---|
| 作业功能要求 | Partially supported | 检索/API/格式链路及 Agent 功能有源码/运行依据；全库新RCTS/LLM-summary迁移和本轮完整复验未完成 |
| Retrieval质量 | Partially supported | 已使用全量语义向量并定位/消融；DEV_Q000目标仍丢失，开发集不足证明整体无损 |
| Answer factual quality | Not supported | 新原生小集仍有主请求不匹配、比较误批和对照退化 |
| Critic生产有效性 | Not supported | 逐issue证明已实现，原生缺陷漏检仍出现，不能用稳定pass作事实证明 |
| Multi作为默认值得采用 | Not supported | 旧同题实验成本更高而正文质量较低，本轮未得到可重复新质量收益 |
| Production release | Not supported | 小集质量门槛未通过，没有生产冻结/完整复验或独立人工事实验收 |

未运行的完整新实验只标记 Not yet verified，不以部分10题代替310题，不设置虚构课程F1及格线。

## 可复现入口与下一步

模型和全量语义服务需按根README准备；以下从仓库根目录运行，生成新目录。
默认入口用`TECHQA_FACT_AUDIT=0`；改为1是开发审核实验，不能当作已验收的生产配置。

```powershell
$env:PYTHONUTF8='1'
$env:TECHQA_PROFILE='full'
$env:TECHQA_DENSE_BACKEND='semantic'
$env:TECHQA_RERANKER='nomic'
$env:AGENT_PROFILE='ollama'
$env:AGENT_RETRIEVAL_BACKEND='techqa'
$env:TECHQA_GENERATION='extractive'
$env:TECHQA_FACT_AUDIT='0'
Set-Location enterprise-ai-agent
$taskRunPath='evaluation/results/techqa_recheck_'+(Get-Date -Format 'yyyyMMdd-HHmmss')
& '../.venv/Scripts/python.exe' -m evaluation.evaluate --dataset '../audit/techqa_root_cause_20261003-01/regression_questions.json' --output $taskRunPath
```

剩余优先项是从用户原始请求构造可验证的检索查询、区分完整比较与单方发布信息、改善P8/Oracle
适用性误拒、提供SPSS具体操作和清理不改变命令语义的展示噪声。更大模型/新重排器/多Agent的收益
仍需同题消融，不能作为已证明的解决办法。先通过成功控制及误接受门槛，再做新的完整复验。
