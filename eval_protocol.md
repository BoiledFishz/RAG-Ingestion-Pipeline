# TechQA 评测协议 v0

本协议先冻结评测，再允许改进检索、生成或审核代码。当前被测系统为 **Enterprise 默认 RAG Agent**，调用完整 TechQA 共享检索管道；不代表其他 Single/Multi-Agent、Research 或 Critic 服务已完成同样的验收。没有新增或合成 QA 语料。

## 1. 原始数据与信息隔离

使用官方 train 600、dev 310、validation 20，共 930 条记录。原始 QUESTION_TITLE、QUESTION_TEXT、ANSWER、DOCUMENT、DOC_IDS、ANSWERABLE 和偏移字段全部保留，不改问题、答案或标签。官方文件 SHA256 写入 splits.json。

相同 title/body 的问题按精确文本 SHA256 组成一个组，避免 train/dev/validation 的别名跨区。共有 891 个问题组、39 条重复记录；6 个组具有不同 Y/N 标签，保留分歧，同组分区。完整评测保留所有原始记录，bootstrap 以问题组抽样，避免重复记录假装独立样本。

历史上 train/dev 已被完整用于调参或评测，validation 也有历史成绩。**本次是回顾性留出，不是从未看过的独立验证集**。此后禁止用 held-out 诊断或设计阈值/守卫；真正的前瞻泛化验证需要另一批尚未暴露的真实官方数据。该限制不会被新的随机拆分消除。

run_eval 的推理子进程只接收 `{"query": "原问题的 title/body"}`。子进程不会收到 QA ID、答案、Y/N、DOC_IDS、DOCUMENT 或 required_facts。目标 DOCUMENT 只在推理返回后用于评分；DOC_IDS 不用于过滤检索范围。代码没有硬编码任何 QA ID 或目标文档 ID。与题目匹配的标识仅存在于冻结数据文件和运行结果中。

## 2. 固定拆分与 held-out 预算

固定种子 **20261004**。按问题组的标签签名 Y、N、Y+N 分层；每层固定顺序后 shuffle，round(0.6 × 组数) 进入 tune，其余进入 held-out。因此在避免重复泄漏的前提下近似 6:4，实际 Y/N 数量记录在 splits.json。

初始化先独占写入 held-out.json，立即计算 SHA256、保存 .sha256，再写 tune 和拆分清单。重新初始化、覆盖冻结文件或更换种子会报错。每次运行重新验证校验和。文件冻结由哈希和拒绝覆盖实现，不能阻止拥有系统写权限的人同时篡改文件及校验和；第三方可使用首次公布的 splits SHA256 核验。

快速集：tune、held-out 各 **20Y + 10N**，固定抽样、问题组互不重复，避免混合标签组和空答案 Y；选择仅依据标签/是否为空，不依据本次输出质量。完整复验使用两分区的全部原始记录，快速成绩不得写成全量成绩。

每配置至少 3 次 native 推理，固定重复编号 1–3、顺序种子 SEED+编号，保持当前模型 temperature=0 和原有 token 预算；不为制造随机性而改默认生成参数。相同结果仍报告 3 次独立执行及其范围，不将 3 次执行当作三倍题目数。

**“阶段末 held-out 跑一次”指一次预注册阶段调用，该调用内完成 3 次重复。** heldout_ledger.jsonl 的 SHA256 链分别记录累计阶段启动数、累计重复启动数、完成/失败。失败也消耗阶段使用权，不静默重跑，不自动恢复或复用旧结果。held-out 只在同阶段 tune 的 3 次重复完成后启动；不在重复之间改配置或查看并利用 held-out 分题结果。未完成的阶段不得作为成绩。额外检查消耗次数必须另设阶段并注明原因，不能冒充首次运行。

## 3. 固定原成功对照集

从已保存的历史 Enterprise semantic-v3 结果中选择 tune 内 10 个独立问题组：Y、官方答案非空、正文 token F1×正确文档引用 ≥0.6。按固定种子哈希排序选择，冻结完整原结果及其 SHA256。这是**历史指标成功**，事实完整性仍需人工确认，不将高 F1 当作事实金标。

对照集与随机快速集分开汇总；若有重叠只执行一次，多出的对照题单独执行 3 次，不计入随机集主指标。报告 v0 相对历史成功结果的已有退化。之后每个单改动相对 v0 按题/重复配对：回答、正确引用、正文 F1，以及双标注事实覆盖均不得下降；任一题下降都标记对照退化，禁止批准上线，不用总体均值掩盖它。

## 4. required_facts 与双独立标注

先仅根据官方答案半自动生成文字分句候选，不查看被测答案。候选是**未审核草稿**，不能直接作为已验证的事实金标。人工先在 human_facts 模板中确认每个 Y 的 2–5 个互不重复 required_facts，分类 version/step/command/condition/other，并提供官方答案中的逐字 reference_quote。不得引入外部知识来修补原答案。长答案的分句抽样可能漏掉关键步骤，人工必须检查。3 条 Y 官方答案为空，不能伪造事实；标为无法从官方答案定义事实、报告缺口，并从该指标有效分母剔除。单句不足两个独立事实的题也保留待拆解标记。

人工事实定义经独占写入和 SHA256 冻结后，才能生成评分表并运行 LLM 裁判。用户担任人工标注者；另一个独立标注者为 **Llama3.2:3b**，被测模型为 **Qwen2.5:7b**。两者不共享评分，不给裁判配置名、官方 F1 或目标文档 ID。人工提交前不得查看 LLM 评分。held-out 人工表仅供评分，不能反馈到同阶段设计中。

逐事实评分：

| 分数 | 定义 |
|---|---|
| 0 | 未提到、错误、与必要事实矛盾；拒答或推理错误没有覆盖事实 |
| 1 | 部分覆盖，但缺少重要版本、步骤、命令参数或适用条件 |
| 2 | 该事实完整、正确地出现在答案正文中 |

正分必须附答案正文中的逐字 answer_quote。来源对象和正文外的来源摘录不能补正文缺失。完整复制一个条件不自动证明该条件适用于提问环境。裁判超时/输出非法保持缺失，不编造 0 分替代。所有 Y 需要有效定义和双标注，才允许将此阶段事实指标视为完成。

对每题，事实覆盖 = Σ事实得分 / (2 × 事实数)，主指标是题目等权宏平均；同时报告得分点数/可能点数。另报告“所有事实均为 2”的题目比例。人工和 LLM 各有独立分数及 CI，不强行产生共识。报告逐事实 0/1/2 完全一致率；分歧保留两个评分、证据和 unresolved 标记。相同题的相同答案哈希可共享一次人工/LLM评分，推理 3 次执行记录仍保留。

## 5. 指标、分母与 95% CI

| 指标 | 分子 / 分母与范围 |
|---|---|
| Recall@5 / Recall@10 | Y 中目标 DOCUMENT 出现在实际共享管道最终前5/10 Chunk 的题数 / 有效 Y 题数；不把 DOC_IDS 全部当相关文档 |
| MRR | 首次目标 Chunk 倒数排名之和 / Y 题数；未召回为0 |
| Context Precision@5 | 每题相关 Chunk 个数/5 的和 / Y 题数；缺席位置记0；属于文档标注代理，不宣称是语义裁判得分 |
| 正确文档引用 | 正确引用目标 DOCUMENT 的 Y 数 / Y 总数 |
| Y 回答率 | 有来源回答的 Y 数 / Y 总数；不等于正确率 |
| N 拒答代理率 | trace=unanswerable 的 N 数 / N 总数；澄清、invalid_evidence、异常不算成功拒答 |
| 正文 token F1 | 仅答案正文与非空官方答案的 token 重叠 F1之和 / 有效 Y 数；另报正确引用乘积；不含 sources 内容 |
| 异常/重排降级率 | 相应事件数 / 所有题数；失败保留在分母，不重复尝试直到成功 |
| 延迟、LLM Calls、Tokens | 实际总量 / 所有题数；包括实际失败调用；不包含评测裁判成本 |
| 事实覆盖、完整事实率、一致率 | 按第4节定义，分别报告有效题数、事实对数与得分点数 |

Recall 观测的是默认共享管道最多20个最终 Chunk，在 parent 扩展前；Agent 实际使用的最多8个 parent 保持原样。两层不能混称。N 的官方标签对应官方 DOC_IDS 范围；完整80万文档可能存在另外的可回答证据，所以 N 拒答代理率**不等于已证明的幻觉率**。

每指标报告每次执行的分子、分母、值，3次均值及 min/max。数值指标使用固定种子、2000次按整个问题组有放回抽样的 percentile bootstrap 95%CI，组内保留重复执行及官方别名。独立快速集的二值指标每次使用 Wilson 95%CI，总体 CI 采用三次 Wilson 区间包络，不合并成虚假的3倍 n。跨事实一致率也按问题组 bootstrap。无观测返回 null。bootstrap 全0/全1可能退化，不能据此宣称没有总体风险。

有效独立问题组少于10（或实际有效分母少于10）统一注明 **“仅描述，不作结论”**。不能用同题3次、同题多个事实或重复官方别名绕过这个要求。题目/事实点数分母同时保留，不偷换单位。

## 6. v0 冻结与单改动消融

冻结默认环境配置、SUT每文件哈希、源码ZIP、模型digest、完整语义索引manifest、Python/依赖、拆分、原成功对照和评测器源码。三次中途 SUT变化使阶段无效。生产检索/生成/审核源码不在本轮修改范围。

两区各3次完成后，冻结 baseline_v0.quick.freeze.json 与原始 summary/runs 校验和。**原生推理基线可先冻结；人工事实定义和双评分缺失时，事实覆盖、一致率返回 null，整个事实验收保持 pending，消融执行被锁定。** 人工评分补齐后，只重新评分已冻结答案，不额外运行 held-out；生成独立 annotation_summary 和 annotation_acceptance，不覆盖原始成绩。最终完整复验另设 baseline-v0-full 阶段，使用全部记录，不把快速结果替代全量结果。

后续配置通过 evals/protocol_v0/configurations/<名称>.json 注册，相对 v0 只允许一个环境参数变化，source、split、模型和其他参数固定；同名称禁止覆盖。当前入口拒绝源代码改动。需要源代码消融时，必须另外预注册“v0源码快照 + 单个可审查补丁”、明确单一假设，并使用同样冻结/计数/对照机制，不能直接接受任意新HEAD。叠加多项改动或在候选配置之间继承改动均不符合本协议。

## 7. 复现命令（PowerShell，仓库根目录）

```powershell
# 首次初始化，仅一次；已冻结后禁止重建
.\.venv\Scripts\python.exe run_eval.py --init
# 原生快速基线；真实模型，两个分区各3次，完整文档索引
.\.venv\Scripts\python.exe run_eval.py baseline-v0 --partition both --scope quick --stage baseline-v0-quick
# 全量复验另设阶段；仅在阶段结束时启动一次held-out
.\.venv\Scripts\python.exe run_eval.py baseline-v0 --partition both --scope full --stage baseline-v0-full
# 人工先只审核官方答案产生的事实定义，编辑模板的副本，然后冻结
.\.venv\Scripts\python.exe review_eval.py --freeze-facts <人工事实文件.json>
# 独立不同模型评分；同stage/partition的数据无需重新推理
.\.venv\Scripts\python.exe review_eval.py --stage baseline-v0-quick --partition tune --judge
# 人工盲评评分表副本，提交命名身份、independent=true和全部0/1/2证据
.\.venv\Scripts\python.exe review_eval.py --stage baseline-v0-quick --partition tune --import-human <人工评分文件.json>
.\.venv\Scripts\python.exe review_eval.py --stage baseline-v0-quick --partition tune --summarize
# held-out按同样流程评分；两区完成后解除annotation锁。不得据其分题结果调参。
```

需要本地 Ollama11434 和已有 semantic 服务11435，模型无需重新下载。默认 top_k、阈值、生成和审核选项均照原生产配置，不进行评测专属扩大或修改。

## 8. 人工授权补充 A1（2026-10-04）

用户明确授权：“允许补充协议，单独报告”。补充仅作用于事实标注，原始 v0 文档副本、评测器 ZIP、推理输出和 summary.json 不覆盖。政策冻结在 annotation_policy.a1.json 及其 SHA256；实现使用独立 review_eval_a1.py，原 review_eval.py 保留供复现。

若官方答案只有一条可独立判定的事实，由具名人工先看官方参考、不看模型答案，批准该事实并说明原因。此类题保留单事实例外，从**主事实覆盖和完整事实率**均值排除，显式报告每次执行的全部 Y 数、有效 Y 数和例外数；对例外题另外报告逐题 0/1/2、完整率和双标注者一致率，分子/分母、95%CI 仍必备，有效独立题数少于10标为“仅描述，不作结论”。不得将空答案伪造为单事实。原成功对照题即使是例外也必须保留，逐题比较，不能借排除从均值中移除对照门槛。

这项授权不表示已人工批准 AI v2 的29题定义。v2 的88条引文已对本机真实官方答案机械校验；同一 AI 起草和自查不计为独立标注。先完成具名人工定义复核，再用人工和不同于被测 Qwen 的 Llama 独立评分；分歧保留。适用规则不含任何 QA/目标文档 ID，对 tune 与 held-out 一致。只重新评分冻结回答，**不重新运行 held-out**。

```powershell
# 在人类已确认定义、填写 annotator / human_approved 的副本上运行
.\.venv\Scripts\python.exe review_eval_a1.py --freeze-facts <人工事实副本.json>
.\.venv\Scripts\python.exe review_eval_a1.py --partition tune --judge
.\.venv\Scripts\python.exe review_eval_a1.py --partition tune --import-human <独立人工评分副本.json>
.\.venv\Scripts\python.exe review_eval_a1.py --partition tune --summarize
# held-out同样只评分已冻结回答，不再执行 run_eval.py
```

新增 annotation_summary.a1.json 与既有 native summary.json 并存；两区双评分都完成后才记录 annotation_acceptance 并解除消融锁。当前仍待人工验收。
