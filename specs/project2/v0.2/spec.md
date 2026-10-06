# Project 2：TechQA 技术支持知识分析规格 v0.2

<a id="s00"></a>
## S00 文档状态与实现前审阅

- 编制日期：**2026-10-05**，America/Los_Angeles。
- 状态：**待用户审阅，尚未授权实现**。本文规定的能力均为拟实现行为，不是运行结果。
- 审阅必须发生在实现之前。人工审阅日期：**未发生，待填写**；审阅人、决定、批准的版本/文件哈希：**待填写**。不将编制日期记成人工批准日期。
- 本阶段交付文档、查询侧任务登记和用户指定的 `check_docs.py` 文档检查器。应用源码、现有 MultiAgentVersion、冻结 v0、官方数据和评测结果保持原状；不运行模型、检索、统计查询或评测。
- 本次修改指令已采纳 CL-01/02/04/05/06/07 的草案建议；不代表整版获准实现。CL-03 待课程确认，CL-08 待标定协议审阅，CL-05 的选型最终确认见 [review_sheet.md](review_sheet.md)。
- 来源：[统一需求 v0.1 原样副本](requirements_v0.1.md)、本地 Chap11–16 HW 和 [仓库复核报告](<C:/Users/zacha/Documents/Ingestion Pipeline/audit/2026-10-05-project2-requirements-review.md>)。副本 SHA256：`7aa3441bf33c7d3b94501d99d6a7e99e0ba486e03413abf3e530c6a847f6ea7b`。原件整合稿的未审阅声明原样保留；复制不构成课程批准。本文增加的预算数值和接口设计是项目建议，不冒充讲义原文。

<a id="s01"></a>
## S01 场景与版本化入口

服务对象是查阅 IBM 公开技术支持知识库的工程师。至少支持以下**组合任务模板**：用户提交一个原始技术问题，要求解释适用的技术证据，同时了解知识库中关于该问题所述产品/版本的词项文档覆盖；有两个版本时可比较两组文档数。

RAG Worker 回答“原文支持哪些原因、条件或操作”，Database Query Worker 独立回答“授权文档全集中，满足明确词项条件的不同文档有多少”。Supervisor 汇合解释、计数、来源和限制。计数不能补足 RAG 缺失的事实，也不能证明某版本受支持、存在漏洞或故障更多。

这是一项应用任务模板，**不是新生成的 QA 测试语料**。官方 `QUESTION_TITLE` 和 `QUESTION_TEXT` 的字符串原样保留，请求 `query = QUESTION_TITLE + LF + QUESTION_TEXT`，不 strip、不补写、不生成新问题；`analysis_operation` 单独传递。标题/正文组合是版本化请求外壳，不回写官方数据。无法无歧义提取时请求用户补充，不臆造实体。

### S01.1 确定性构造与先登记后运行

1. 唯一抽样来源为冻结 `evals/protocol_v0/tune.json`；仅投影 `QUESTION_TITLE`、`QUESTION_TEXT`。不读取 held-out 内容；QA ID、DOC_IDS、ANSWER、ANSWERABLE、官方偏移和检索结果均不参与任务类型、抽样或查询构造。目标 ID 仅在之后独立评分器中使用。
2. `techqa-query-task-v1` 的实体、版本、平台、错误码/命令字面规则在 [task_preregistration.json](task_preregistration.json) 的 `sampling_rules` 原样登记。匹配跨度指向原 query，不能生成别名；错误码/命令只作查询侧标记，不增加 DB 白名单字段。抽样阶段的版本候选只决定类别，不等于DB已接受的谓词。在线计数优先取标题中的首个明确实体；比较必须取得两个**实体—版本关系明确**的组：版本跟在最近实体之后、间隔不超过32字符且不跨另一实体，按原文顺序取前两组。需要扩大到组件名时只能使用原文现有跨度。不能将两个不同产品的版本都绑到首个实体。若候选实为IP/XML数值、关系冲突或无法组成两组，则clarification_required，不能擅自宣称completed；规则不认定技术适用性。AC12-11固定使用登记的P2-COMPARE-03中两个明确产品/版本组。
3. 按完整 query 的 SHA256 去掉逐字重复；固定种子 **20261005**。排序键为 `SHA256(十进制种子 + ':' + query_sha256)`，按十六进制字符升序。互斥分层优先级为：至少两个不同版本候选→compare；否则含平台→platform；否则含错误码/命令候选→identifier；否则含版本→version；其余有实体→entity。各层取前 8 条。层内不足必须停止登记、重新审阅协议，不跨层补数、不生成样本。
4. 在上述 40 条之外，按 query 字符长度升序、上述排序键破同分，取前 10 条作 `no_answer_challenge`。这个名称是**预登记无适用答案假设**，不代表已知 N 标签或真实无答案；不根据答案/标签/检索结果筛选。发现可回答必须保留问题、判相应无答案场景失败，禁止看输出后换题。
5. compare 构造 `analysis_operation=compare_document_counts`，其余为 `document_count`；DB 谓词仅由原 query 槽位生成，使用 S04 的 literal phrase 和服务端可信范围。示例请求最多每组 5 行。版本/平台不明时仍保留原 query，拒绝隐式补齐。协议故障/非法操作只能改独立的配置或 Contract 字段，不能修改原问题/源文档。
6. 样本在 **2026-10-05、任何 Project 2 请求运行之前**登记。登记文件含逐字标题/正文、query 哈希、类型、跨度、排序键和独立操作；无 QA ID、目标 ID、答案或标签。登记后保持冻结，修改必须升规则/任务版本、另行审阅，不覆盖当前登记。当前登记 SHA256 为 `ecd190e06afc173ab485ccba8c1a16e6256ede19b575ecd1ceb00891de86d63f`，同时记录在 `.sha256` 文件。此处日期是登记日期，**不是人工审阅日期**。

| 任务类别 | 固定样本量 | 操作 | 用途 |
| --- | ---: | --- | --- |
| compare | 8 | compare_document_counts | 两组版本词项计数/交集；歧义显式失败 |
| platform | 8 | document_count | 平台限定的技术解释与计数 |
| identifier | 8 | document_count | 含错误码/命令的原问题；不生成命令 |
| version | 8 | document_count | 单版本条件的解释与词项覆盖 |
| entity | 8 | document_count | 产品/组件词项覆盖 |
| no_answer_challenge | 10 | document_count | 无适用答案的预登记挑战，不使用 gold N |
| 合计 | **50** | — | 前 40 条为预算标定池，后 10 条单独保留 |

验收 CSV 的每个输入都给出已登记的 sample_id、**具体原 query**和操作，不使用将来选题占位符；多个状态测试可复用同一原 query，仅隔离注入状态/计时/权限元数据。不能把 42 个场景或三重复当作 42/150 个独立问题。原 QA 黄金评测仍遵守已有 quick 集至少 20 Y/10 N，业务分层与 Y/N 分层不是同一概念。

拟新增入口：独立应用 `api.project2_main:app` 的 **POST /v1/project2/analysis**，合同版本 `project2-v1`。Project 2 应用默认使用本规格的 Supervisor、策略和预算；不存在绕过它们的备用默认路由。原 `api.main`、`/v1/multi-agent` 和 MultiAgentVersion 保持原行为。CL-06 的入口方案已按本次指令采纳，尚未实现。

<a id="s02"></a>
## S02 核心在线 Worker 选型

打分是设计判断，**不代表已实现或经过性能测量**。各项 0–2：0=不满足/无合法依据，1=需补充定义或条件，2=按当前源字段能够明确设计。总分只是选型辅助，不能替代课程验收。

| 候选 | 符合 Chap12 核心定义 | 数据合法 | 独立于 RAG 候选整理 | 可独立验证 | 合计 | 建议 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| A：Database Query Worker，授权 TechQA 文档全文词项计数/比较 | 2 | 2 | 2 | 2 | 8 | 推荐；使用现有关系表与 FTS 索引，返回明确数据结果，不需要新业务字段 |
| B：Analytics Worker，登记 `text-length-profile-v1` 统计文档长度分布 | 2 | 2 | 2 | 2 | 8 | 本轮不选；可从原 title/text 合法计算，但长度分布不回答本场景的产品/版本覆盖计数，且不能代表技术质量；增加统计模型 Contract 没有当前需求依据 |
| C：Domain/API Worker，再调用文档搜索 API 并整理 Top-k | 1 | 2 | 0 | 1 | 4 | 拒绝；当前只有同一文档检索能力，职责重复 RAG，缺独立领域服务结果 |
| D：Analytics Worker，产品/版本“支持趋势或风险预测” | 0 | 0 | 2 | 0 | 2 | 拒绝；没有可确认的业务时间序列、暴露量或故障观测，无法合法预测趋势/风险 |

总分相同也要按实际任务选择。A 直接提供本场景要求的独立计数/比较，B 是可行但不必要的另一个分析方向；不为了增加 Agent 数量同时实现二者。推荐 A 的前提是将业务明确为“技术支持知识资产查询”，而非客户运营或销量分析。CL-05 按本次指令采纳 A 作为草案，最终选型确认留在确认单，不表示课程适用性已获老师认可。**AC12-11（真实比较/部分计数边界）和 AC12-13（全母体计数不受 RAG 候选改变影响）为必过项**；仅有文字论证或 Mock 不得通过核心 Worker 验收。若选型不获确认，应先确认另一项合法能力，不虚构数据或包装证据整理节点补足。

**共用文档库仍能构成不同能力的理由与可证伪测试：**

1. 数据库 Worker 的输入是有限的词项谓词/操作；不接收 RAG 候选列表、chunk_id、相关性分数、重排顺序或官方目标 ID。RAG 的 Top-k 不是统计母体。
2. 它对整个**授权文档集合**执行 COUNT/集合运算，单位是不同原始文档；RAG 执行向量/BM25 排名并选择少量支持片段。二者解决不同的数据问题。
3. 它输出可独立复算的数值、查询条件、数据快照、测量完整性和例示来源；不输出原因诊断或引用摘要来冒充数值结果。
4. 独立运行时不需要 LLM、向量服务或 RAG；关闭这些依赖后，合法数据库查询应仍可返回真实计数。
5. 保持文档快照和谓词不变，改变/清空 RAG Top-k、相关性排序和生成提示词，数据库计数必须完全不变。SQL 计数应与独立只读复算一致。若计数随着候选集变化，该实现不合格。

<a id="s03"></a>
## S03 数据来源、快照与派生规则

只使用官方 TechQA `technote_corpus/full_technote_collection.txt.bz2` 的原始文档。现有 `rag.techqa.data.normalize` 和 `rag.techqa.index` 将原字段投影为 `docs(doc_id,title,text,metadata)`，并建立 `search` FTS5。Worker v1 只使用 **doc_id、title、text**；不把 metadata 中未核实的时间/产品标签当权威业务字段，不读取 QA 文件或评分 sidecar。

数据版本由现有官方归档 SHA256、`manifest.source_archive_sha256`、scope、format_version 和完成标志绑定；归档预期 SHA256 为 `6b094ef9a69718f727ce8d7e15c4d961e51032cefaa952e0d6af9d176d7ba118`。文档数从经校验 manifest 读取，不在新 Worker 中硬编码数量。归档/schema/tokenizer 不符或索引未完成时拒绝统计并记录 `failed/data_version_mismatch`，不静默降级到小样本。

| 派生规则版本 | 来源字段 | 规则 | 结果及限制 |
| --- | --- | --- | --- |
| `techqa-doc-projection-v1` | 原始 id/title/text | 沿用现有只读标准化投影；同一原始 doc_id 计一次；空正文按既有库存规则排除 | 统计母体是该快照中的可用文档，不是所有可能的 IBM 资料 |
| `techqa-fts-predicate-v1` | title、text | 沿用 `porter unicode61` tokenizer；参数作为转义后的完整 FTS phrase；多个实体/版本/平台 phrase 用 AND | 这是词项/词干匹配，标点和大小写按 tokenizer 处理，不是语义适用性或精确字符匹配 |
| `request-slots-v1` | 用户原始请求 | 确定性抽取原请求中的明确实体、版本、平台字符串，保存原文跨度；无法确认则返回补充请求所需字段 | 不用官方答案/标签/目标；不依赖模型生成新的别名，不改写原问题 |

不建立支持版本、销售、工单、故障率或日期的伪字段。没有可靠时间字段时不支持时间趋势。Tokenizer/抽取规则改变必须升版本、记录影响并走单改动验收；不覆盖源数据或冻结索引。

<a id="s04"></a>
## S04 指标、查询白名单与规模限制

令 D 为服务端授权范围内、当前快照的不同非空文档集合。M(d,p) 表示文档 title/text 满足已记录的 FTS phrase 谓词 p。

- `document_count(p) = |{d ∈ D : M(d,p)}|`，单位“原始文档”。同一文档多个 Chunk、多个词项命中不增加计数。
- `compare_document_counts(pA,pB)` 返回两个独立计数、交集计数与有符号差值 A−B。A/B 不互斥；不得将两组计数相加称为不同文档总数。每个已发布计数必须覆盖全部授权匹配集合。
- `list_matching_documents(p)` 仅提供例示 doc_id/title/匹配字段；默认每组 5 行，最多 10 行、最多 2 组、整条响应最多 20 行。不是完整结果下载，不以样本行数作为文档总数。

操作白名单只有上述三项。最多两组谓词，每组最多产品/组件、版本、平台三条 phrase；每条最多 120 字符。引用、运算符等用户文本作为 literal phrase 转义，SQL 只允许程序持有的参数化模板。用户、Prompt 和计划都不能提交 SQL、表名、列名、文件路径、URL、任意 doc_id 或任意可执行代码。只读连接、只读 SQL 白名单、查询取消与规模限制由程序强制。

统计可遍历整个授权集合；不人为截断计数母体来满足返回行数上限。单次 DB 语句默认 12 秒，整个数据库 Worker 最多 25 秒，均受 S08 的请求剩余时间限制。超时返回 `timeout` 或比较中的 `partial`，**未完成计数为 null**；不得把已扫描前缀作为精确总数。样本行数被限制只设置 `samples_truncated=true`，计数完整时不单凭样本截断改成 partial。

必须随每个统计结果返回的 limitations：

- “文档数是词项匹配的知识库覆盖计数，不是工单量、故障率、用户数、产品使用量或销售指标。”
- “包含产品/版本词项不证明该版本受支持、受影响或适用于用户；技术适用性由 RAG 依据原文解释。”
- “同一文档可命中两个比较组；tokenizer 的词干和标点处理可能扩大字面匹配。”
- “统计只覆盖明确授权的数据快照；示例文档为有限行，不代表完整清单。”
- 比较 partial 时指出哪组计数缺失；零匹配只有在完整查询成功时才可表示 count=0。

<a id="s05"></a>
## S05 请求边界与可信授权

业务输入包括原始 `query`、白名单 `analysis_operation`、明确的请求范围收窄条件和是否需要样本。原 query 单独保留，检索 query 与数据库谓词分别记录。用户不提供身份、Tenant、资源授权、目标文档 ID、官方答案或 Y/N 标签；这些键不属于在线 Contract，拒绝未知字段。

`TrustedContext(subject_id,tenant_id,allowed_corpus_scopes,allowed_operations)` 由已认证的服务端上下文构造。CL-07 采纳初版服务端受控凭证→主体/权限映射；若复用已有可信网关，服务仍验证其认证来源，不接受任意客户端 header 自报身份。不新增登录产品。网络位置、请求正文自报身份、任意 header 值、Prompt 和 LLM 计划均不授予权限。

Policy 对主体、操作、语料资源、运行状态资源逐项检查。用户过滤只能收窄权限；授权全集由程序限定，两 Worker 使用一致的主体/范围。现有 published 过滤保留，但不将它冒充身份认证。授权输入来自服务端策略，不依赖 TechQA 原文 metadata 自报 ACL。

全局身份无效/无任何请求权限：`permission_denied`，两 Worker 零调用，不返回缓存/Checkpoint 内容或受限资源是否存在。CL-02 已采纳：单 Worker 操作拒权时只运行另一条独立且合法的任务，整体不得 completed。所有分支先验权，Resume 与返回旧结果前再次验权。doc_id 仅可作为实际授权查询/检索的输出或内部来源定位，**评分目标 ID 绝不成为输入或选取依据**。

<a id="s06"></a>
## S06 Worker Contract 与状态子集

公共结果外壳：`contract_version,run_id,task_id,worker,status,payload,evidence,limitations,error,usage`。未知成本/取消输出 Token 为 null；估算与观测计数分列。错误包含稳定类别、是否可重试和缺失能力；不含凭证或未授权内容。Worker 不决定最终整体状态。

| Worker | 状态子集 | 明确定义 |
| --- | --- | --- |
| RAG Worker | completed / partial / no_data / permission_denied / timeout / failed | completed=本次引用有效且现有证据判定覆盖请求；partial=有明确可回答部分并列出缺口；no_data=没有可发布证据；拒权/超时/错误与知识库不足分开。completed 是程序按规则得出的服务状态，不等于人工事实正确认证 |
| Database Query Worker | completed / partial / no_data / permission_denied / timeout / failed | completed=所需计数精确完成；partial=例如比较中仅一组精确完成；no_data=成功完整查询但无匹配（count=0、measurement_complete=true）；拒权/错误/超时的缺失值为 null，不置零 |

数据库 payload 包含操作、各组 predicate、已完成 count、交集/差值（依赖项缺失则 null）、unit、measurement_complete、有限 samples、快照/rules 版本、授权范围标识和 samples_truncated。不向模型暴露未授权结果；不产生原因、支持结论或预测。

计划是有限注册任务：`rag_explain`、`techqa_document_query`，固定依赖和汇合阶段；默认不启用 LLM Planner。两 Worker 输入来自同一个已校验请求，不互相传递无限历史。最终渲染由 Supervisor 所有；Worker 只写各自结果、预算器写消费量、Runtime 写生命周期。新增任务必须通过 Contract/Policy/预算校验，不靠模型枚举自行增加能力。

<a id="s07"></a>
## S07 程序计算的整体状态

CL-01/CL-02 已按本次修改指令采纳。组合任务两个 Worker 都是必要能力；有有效结果而另一能力缺失时整体 partial。`has_useful_result` 必须由已校验的有效证据或至少一个精确统计结果证明，不能仅看非空字符串；未完成数据不能算有效结果。

| RAG 状态 / DB 状态 | completed | partial | no_data | permission_denied | timeout | failed |
| --- | --- | --- | --- | --- | --- | --- |
| completed | completed | partial | partial | partial | partial | partial |
| partial | partial | partial | partial | partial | partial | partial |
| no_data | partial | partial | no_data | permission_denied | timeout | failed |
| permission_denied | partial | partial | permission_denied | permission_denied | permission_denied | permission_denied |
| timeout | partial | partial | timeout | permission_denied | timeout | failed |
| failed | partial | partial | failed | permission_denied | failed | failed |

表格前置规则：全局授权失败直接 permission_denied，不调 Worker；schema/未注册操作/缺少无法推断的输入直接 failed，附 invalid_input 或 clarification_required，不伪装 no_data。请求截止时取消未完成分支：已有可发布结果则 partial，否则 timeout。已确认拒权具有最高优先级；不能用随后超时掩盖拒权。上述计算及对保留结果的授权复查必须独立于 LLM。

矩阵单元的稳定引用格式为 `S07[rag=<六态>,db=<六态>]`，如 `S07[rag=no_data,db=completed]=partial`。验收 CSV 每行写一个具体单元及精确整体状态，不用“依 S07”或任选多个状态；36 对覆盖由 AC12-14 的参数表另外逐格验证。调度前拒绝时 Runtime 为两个逻辑任务写 permission_denied 或 failed 的终结记录，`execution_started=false`、调用数 0；不是声称 Worker 实际执行。文档/构建/停止资源类场景的状态指该场景明确附带的服务探针或门禁预期，行政动作本身不冒充 Worker 响应。

终态输出：`status,answer,evidence,data_results,limitations,worker_results,run_id,trace_id,usage`。partial 明确“已覆盖什么/缺什么”，不能计入完整回答。无匹配的 count=0 保持零值和查询成功信息；依赖不可用的 null 不能变成“无匹配”。权限失败只给非敏感理由，不泄露被拒资源内容/存在性。

<a id="s08"></a>
## S08 默认 API 强制总预算

**CL-08：待标定**。90/16/6 及各依赖超时仅为标定前临时值，不是已选定生产参数或已测性能承诺：

| 预算 | 默认建议 | 强制位置 |
| --- | ---: | --- |
| 整条请求绝对截止时间 | 临时 90 秒 | 新 Project 2 API 在验权/分派前建立；贯穿输入处理、两 Worker、渲染、取消和状态保存 |
| 所有依赖实际尝试总数 | 临时 16 | 每个 LLM/HTTP/工具下游/DB 语句边界调用前原子预留；失败、取消和重试均消费 |
| LLM 请求上限 | 临时 6 | 总预算子集；调用前检查并计数 |
| DB 单语句/Worker | 12 秒 / 25 秒 | 取本地上限与请求剩余预算的最小值；SQL progress/cancel 与连接清理 |
| 模型单尝试上限 | 30 秒 | 同样受剩余请求时间限制；不能先耗满依赖自身超时再检查总预算 |

Worker 调度包装本身不和其内部实际调用重复计数；本地纯解析/格式化不计依赖调用，但耗时仍计截止时间。向量/重排缓存命中若不实际调用模型则计实际 DB/缓存查询，而非伪造 LLM 请求。现有共享检索服务内部外部调用如不可观测/不可取消，必须补充跨服务预算 Contract；缺该能力不能签收端到端总预算，不能仅计外层一个 HTTP 后宣称内部受控。

默认顺序执行 DB 计数→RAG，优先得到可复算结果；不强制并行。预算超限停止新调用、取消/终止在途工作，保留已计尝试与未知成本，按 S07 降级。不能通过普通返回、异常路径、重试或另一个路由跳过预算器。Resume 不重置截止时间、调用数或子预算。当前 MultiAgentVersion 的预算/行为不在本阶段修改。

### S08.1 tune-only 标定协议（待用户同意，未执行）

- 样本：S01 登记的 compare/platform/identifier/version/entity **各 8 条，共 40 条**，每条 3 次，共 **120 次请求**。无答案挑战 10 条不用于预算选值；固定实例/硬件、语料及索引 SHA、模型/提示词 A/检索/策略版本。冷缓存、热缓存条件分别记录，三重复采用“第一次冷，第二/三次相同可解释热状态”；按 40 个独立问题聚类，不把 120 当独立样本。不读取 held-out，也不以答案/标签过滤慢题。
- 先登记标定 profile、样本登记哈希、配置哈希、执行顺序（按 sample_id 及重复序号升序）、取消与重试规则，之后才运行。保留全部超时/失败/拒权/partial，不删除慢题或择优补跑。临时 90/16/6 仍在默认 API 路径强制；标定不是绕过预算的备用入口。
- 测量：端到端墙钟延迟、DB语句/Worker耗时、RAG/检索/重排/模型耗时、实际依赖尝试及分类、LLM次数、Token观测/估算与未知数、取消完成耗时、超限原因、六状态比例。记录计数是否完整和来源适用性；质量规则/拒答阈值不随标定改动。每项报告分子/分母，均值/范围以及按题聚类 bootstrap 95% CI（10,000次，种子20261005），比例另报 Wilson CI；n<10仅描述。
- 可识别性门槛：若任何样本因临时时间/调用上限截断，或内部实际调用/取消不可观测，标定仍为**未完成**；不得用截断后的成功子集估计无条件P95。记录右删失和失败，请用户审阅更大的临时 envelope 后，另登记 tune 标定阶段；不擅自抬限、不触及 held-out、不把故障改为无数据。
- 选值方法：仅在无预算右删失、调用可观测且所有故障可解释时形成建议。冷/热条件分别计算端到端P95的bootstrap95%上界，取较大者U；请求截止候选=`向上取整至5秒(1.25×U)`，不得用混合缓存均值低估冷请求。DB语句、DB Worker、模型单尝试同法（向上取整至1秒），并受总截止约束。总调用候选=`登记合法路径的理论最大实际尝试数+2`，LLM候选=`登记合法路径的理论最大LLM尝试数+1`；分别列出观测最大值并校验不超候选。冗余只防实现边界，不允许新增调用/无界重试。若理论边界无法给出，则不冻结。小样本分位数仅用于候选预算，不构成SLA承诺。
- 候选超出本次临时值不自动生效。用户审阅成本/质量/状态分布后，把最终参数、规则、版本、全部原始测量及选择理由写入 `evals/project2-v1/calibration/budget_frozen.json`，记录该文件 SHA256及标定报告/配置/样本哈希；默认 API 读取这一冻结版本。当前文件不存在，**最终值及冻结哈希未产生**。State 24小时、Trace 7天是临时保留策略，另外审阅数据保留理由，不由延迟P95推导。
- 冻结后该阶段末 held-out 仅一次阶段调用（三重复），按 S14 入账；如失败，保留结果，不再次选值。更改预算需新版本/单改动对照。此文档阶段标定/held-out新增次数均为 **0**。

<a id="s09"></a>
## S09 Evidence、答案边界与可答性

复用 Project 1 的 Retriever/Parent/压缩/引用能力和冻结提示词 A，不另建向量库，不降低拒答阈值。Adapter 保留原 chunk_id、文档、页/偏移、检索排名/分数及压缩片段映射；引用只指向当前授权的实际证据。RAG 原问题/实际检索问题/回退原因分别进入 trace。

统计来源用查询结果证据 ID（如 Q1），技术片段用来源 ID（如 S1），由程序分配并验存在/语义边界。统计只支持明确的数值陈述，不能支持故障因果。空检索、证据不足、无效引用、适用性无法确认时按 Worker Contract 返回限制或失败，不用计数代替技术证据。

若保留 confidence，沿用“未校准的证据覆盖启发值”的说明，不称正确概率；来源存在不能证明内容正确。请求版本/平台不匹配、步骤/参数不完整的已有缺陷继续在独立事实评分中验收，不因新 Worker 成功就认定已修复。

<a id="s10"></a>
## S10 Chap13 Runtime、策略与 Trace

拟新增服务运行状态存储，与评测进度文件、文档索引分离。运行 ID 独立于 Workflow 定义；state 包含 owner/tenant、策略版本、原请求哈希/最小请求内容、数据/规则/模型配置版本、已校验任务、各 Worker 结果、已预留调用数、绝对截止时间、生命周期和终态。

状态写入时点：验权后创建运行、调用尝试预留、Worker 结果验证后、终态/中断处理。进程停止/重启后，以同一 run_id 恢复并复核身份/资源和版本；完成且仍合法的节点跳过；未知/非法/过期/越权状态明确拒绝。只读尝试结果未知时，保留已消费尝试，可在剩余预算中有界重试，不能改成零调用。

默认最小 State 保留 24 小时，Trace 元数据 7 天（待审阅）；不默认存完整 Prompt、凭证或无限正文。Checkpoint 如需证据正文仅保存已授权最小片段并限制读取；返回旧结果前重新验权。调试仅记录非敏感 run/request/trace ID、父子 Span、节点、起止、状态、错误类、预算与脱敏摘要，访问/保留策略须有程序和测试证据。

本项目业务能力全只读；Checkpoint/日志的内部写入不等于业务写操作。默认建议不做 Fake Publish，不启用真实审批路径；提供只读允许/拒绝策略与未来业务写操作的审批、草稿版本、幂等边界说明。CL-03 如改选演示，必须隔离、不连接真实系统，另走规格变更；它不构成核心 Worker 或真实外部副作用验收。

<a id="s11"></a>
## S11 Chap15 可靠性与成本

选择新 Project 2 的 TechQA DB 与复用模型/检索依赖为边界，逐项记录失败类别与副作用。本阶段只规划，不执行故障或性能试验。

默认 DB 查询不自动重试；invalid_input、permission_denied、Policy Violation、版本不一致不重试。可恢复连接故障是否一次重试必须在剩余总预算内明确登记。复用模型的格式修复不超过现有上限，同时受总预算限制。降级保留未完成能力，不标 completed。

新 Worker 不新增结果 Cache、Circuit Breaker、并行或 Queue。既有检索/重排缓存仍在范围内，必须记录文本/模型/索引版本和权限边界；授权必须在缓存返回之前校验。只读业务无外部写幂等要求；Runtime 重复恢复和尝试预留的幂等仍须测试。

在同一 TechQA tune 输入、授权范围、数据版本、缓存状态和模型配置下，比较单 Agent/固定流程与新组合流程，以及选定可靠性改动前后。记录实际尝试、模型/工具计数、Token 观测或估算、延迟和失败。至少三重复、CI 与范围按 S14；诊断一个真实失败再同条件复测，不宣称未经验证的 SLA。

<a id="s12"></a>
## S12 Chap14 容器范围

仅为实际独立服务准备 Dockerfile/Compose/.dockerignore。API 与实际需要的语义/模型依赖按真实边界编排；不把每个 Worker 变成容器，不复制 `.venv`、Secret、原始大数据到构建上下文。容器间使用 Service Name；只映射必要端口。

文档索引/向量及 Checkpoint 存储挂载位置和保留边界须明确。健康检查分存活、依赖就绪和真实业务请求，不能用 TCP 可连接证明业务健康。干净构建→原始 TechQA 组合请求→相关 stdout/stderr 日志→停止保留卷，均须真实运行证据；全量体积风险只在 plan 登记，本阶段不测量/构建。

<a id="s13"></a>
## S13 Chap16 云端范围与执行前提

拟选择课程允许平台，但本阶段不选购、不登录操作、不部署，不核验价格或账号。云平台/远端资源/系统级依赖/PR 操作必须另获用户明确授权。

后续证据应包含真实 Project 2 Endpoint 的 Health 与 TechQA 组合请求、Runtime Secret/监听端口/外部持久状态、同运行 ID 的预期重启/重部署恢复、非生产受控故障的 Cloud Log↔Agent Trace 关联根因与同条件复测，以及停止资源后残留计费核查。公开原文仍按最小字段/脱敏策略输出，不能为云演示生成替代语料。没有这些真实记录，CLOUD 条目保持待实施。

<a id="s14"></a>
## S14 冻结评测协议与对照

沿用 `eval_protocol.md`、`splits.json` 及 SHA256 `688a76605901e5f770fbc74b60c89d4b07eabae8e264055e16f84d5967b69087`；tune 用于设计/诊断，held-out 封存。不得更改原始问题、答案、DOC_IDS、Y/N；在线代码不加载 QA 答案/标签/目标 sidecar，不硬编码 QA ID/目标文档 ID。原始 technote 正文是合法知识来源，不禁止正文自然包含参考答案支持内容；禁止的是将评测答案作为在线输入。

QA 配置比较为冻结 v0 + 单个改动，其余提示词、模型、阈值、数据和预算保持对照；新 Project 2 的架构组合比较另列，不能伪称单改动答案质量提升。业务任务用同一权威 TechQA 来源及未改原问题、版本化任务 Contract，不生成新 QA 黄金答案。旧基线无法执行业务任务时记 unsupported，不伪造单 Agent 成功。

每配置三次重复；分子/分母、均值/范围、独立题数及 Wilson/按问题聚类 bootstrap 95% CI；n<10 仅描述。原成功对照逐题零退化、N 误接受不高于 v0、partial 不计完整回答、required_facts 双评分及分歧保留。不得为了改善接受率下调拒答阈值。TechQA N 是原候选范围标签，全库无答案结论继续保留范围限制。

held-out 仅在每阶段完成、配置锁定且用户允许评测后执行一次阶段调用（三重复），记录累计阶段/重复次数；即使失败也不择优重跑。本阶段新增运行次数为 **0**。新业务计数验收不使用 QA 目标 ID/答案选文档；与答案事实覆盖分开评分，不能挪用旧 QA 金标证明业务指标正确。

<a id="s15"></a>
## S15 非目标及不采用原因

| 项目 | 默认建议 | 原因及条件性后续 |
| --- | --- | --- |
| 业务写操作/真实 HITL | 不采用 | 官方文档只读，无真实写需求；不虚构工单/发布能力 |
| Fake Publish | 不采用，待 CL-03 | 不连接业务能力且不能补核心 Worker；若课程需演示另行隔离 |
| Text-to-SQL | 不采用 | 三个程序白名单模板足够，减少不受控查询面 |
| MCP/A2A | 不采用 | 本地接口与已存在检索服务足够，没有独立远程 Agent 生命周期需求 |
| Queue/独立业务 Worker 服务 | 不采用 | 尚无已测长任务/流量需求；预算不足先显式 timeout，不引入无依据架构 |
| LLM Planner/Replan | 不采用 | v1 两种有限任务固定路由，避免新自由计划风险 |
| 并行/共享聊天历史 | 不采用 | 顺序流程先验收；不以并行或更多 Agent 数量为目标 |
| 可选 Critic | 不采用，CL-04 已采纳 | 当前盲测未达生产门槛；保留程序引用/状态/权限校验，不改变旧 MultiAgentVersion |
| 新结果 Cache/Circuit Breaker | 不采用 | 尚无本路径的故障/性能证据支持；既有缓存边界仍需验收 |
| LangSmith/新增长期 Memory | 不采用 | 结构化 Trace 与最小运行状态满足当前范围，不增加第三方数据与长期记忆 |
| 销售、工单、故障趋势预测 | 不采用 | 官方 TechQA 无所需事实/分母/时间序列，不补造 |
| 新向量数据库/重新建 RAG | 不采用 | 复用现有语义检索和 Project 1 能力 |

<a id="s16"></a>
## S16 验收与证据分类

每项验收必须标明 **真实运行 / 契约测试(Mock) / 故障注入 / 未执行**。故障注入不能替代自然成功路径，Mock 不能证明模型、数据依赖、容器或云已运行。计划的证据路径写“预期路径”，文件不存在时不得写完成。

`traceability.csv` 覆盖整合稿全部 49 个 PRE/RAG/MA/RT/ENV/REL/CLOUD ID，状态全为待实施；另增12个本地 ID。source引用本地需求副本；补充项显式标为“用户补充”并附spec来源，不伪称出现在官方需求表。每行记录相同 requirements_sha256。计划测试/证据类型/预期路径是该需求全部关联场景的去重集合，一对多时用分号分列，避免只标Mock却关联真实运行。`acceptance_scenarios.csv` 共42行，status全待实施，实际结果/实际证据类型全未执行，evidence_file全空；预期路径不是实际文件。

**AC12-23** 是新增的真实依赖“知识库无适用答案”组合挑战，预期 `S07[rag=no_data,db=completed]=partial`。它不注入空检索，不用官方N标签证明全库无答案；固定P2-NOANSWER-01原问题，正常依赖及获准范围，实际运行后由独立审核核对证据缺口。如果真实证据充分或计数为零，必须如实报该预登记预期未达成，不能改题/改阈值/换样本后宣称通过。当前仅登记 planned_evidence_type=真实运行，actual=未执行，**没有新增真实运行证据**。

`python specs/project2/v0.1/check_docs.py` 仅检查需求覆盖、双向引用、具体输入/状态单元、原问题投影/登记哈希、证据集合及全未实施字段；不导入应用、不调用模型/索引/数据库，不填系统验收结果。检查通过只是文档一致性，不代表功能、课程或人工审阅通过。

验收包含：核心 Worker 独立性和精确计数、六状态与全组合汇合、授权/白名单/规模限制、调用/时间预算、RAG 来源与事实质量、实际服务重启恢复、容器请求和云端诊断。完整 Done 需要 Chap12–16 必需项及触发的条件项有可复现证据；不采用项提交决定。此文档阶段不签收任何系统能力。

<a id="s17"></a>
## S17 SDD、变更和阶段提交

先审阅 spec/clarifications，再审阅 plan/tasks 的方向与边界，明确批准版本/日期后才进入实现。未决选择改变状态、权限、Worker 选型或成本时，先更新本版本或新版本，不由实现者默默取默认值。

后续最小新增模块见 plan；每个 Chap12→16 阶段保留命令、实际结果、限制和 Diff。沿用当前仓库和受保护的分支流程，分支命名服从仓库约定。git push、创建/合并 PR、云平台操作、安装系统级依赖均需要用户先批准；不能把讲义示例命令当授权。缺失的历史审阅记录如实登记，不能事后补造“实现前已审阅”。

<a id="s18"></a>
## S18 v0.2 数据期望/谓词限定修订（2026-10-05授权）

本节仅覆盖AC12-02、AC12-03的数据零值前提，以[approval_addendum.md](approval_addendum.md)所录用户授权为依据。其余章节原样继承，审阅前声明按原审批记录解释，不代填审阅。原问题登记及冻结评测协议不变。

旧版AC12-02的默认词项组`Netcool/Impact AND 6.1.0`独立计数为192；AC12-03的默认组`MQ AND V7.0.1`独立计数为1873。二者不能作为真实零值前提。两场景仍保留原query、操作、Worker状态、S07矩阵单元、门禁与证据类型；只把独立统计的零值谓词更换为下表的真实产品/版本词项组。技术解释仍使用原query，不把统计谓词当作新技术问题，不改权限或RAG适用性/阈值。

| 场景 | 统计谓词（两个literal phrase，AND） | 独立全集计数 | 两个phrase的独立边际计数 | 原状态不变 |
| --- | --- | ---: | --- | --- |
| AC12-02 | `mq`；`version 9.3.0.2` | 0 | 18296；2 | RAG=completed;DB=no_data → partial |
| AC12-03 | `websphere  mq`；`9.5.2.6` | 0 | 13881；6 | RAG=no_data;DB=no_data → no_data |

这些是词项匹配统计条件，不声明上述版本属于或适用于相应产品。零匹配不等于官方无答案或产品不支持。AC12-03依然是RAG状态契约测试(Mock)，但数据库零值前提必须真实复算，不用Mock固定数冒充真实统计。AC12-23真实无适用答案的门禁及原始问题完全不变。

登记文件[zero_predicate_registration.json](zero_predicate_registration.json)，SHA256=`317217920ffea15edab5578518114dbcb31cdf78059bbe920872afc08953701d`。算法`corpus-product-version-zero-v1`：只读全部官方文档title；按已批准的实体/版本字面规则识别实际产品—邻接版本（不跨另一实体，间隔不超过32字符）；记录出现频数；从所有实际产品与实际版本组成未在标题中共现的候选对，按`SHA256(20261005 + ':' + product + ':' + version)`升序；完整FTS复算AND与两个边际，取前两个AND为0且边际均>0的不同产品组。登记完整尝试序列、语料manifest、规则、候选统计哈希。选择不读QA内容、问题登记、Worker或模型输出，不生成缺失词项。

在这两条验收输入中，以独立统计谓词`analysis_predicates`记录已登记literal组（不是sample_id、DOC_IDS或任意SQL）；它是S05已有明确统计条件的具体值，不能授予或扩大主体/资源权限，仍受S04的两组/三phrase/120字符及白名单约束。仅上述零值验收以此数据谓词覆盖S01.1第5项的默认槽位组；正常业务、标定40题及所有其他场景仍用原问题槽位。RAG不接收统计谓词，不受其计数或词项影响。

独立只读核对由`scripts/spec_preflight.py`实现，不导入Worker或目录构建器。证据为`audit/project2-v1/preflight_v0.1.json`及`preflight_report.json`；每个场景同时登记规格期望、全集复算及一致/冲突。版本不匹配场景已有真实fixture索引scope可与full区分，保留隔离故障注入，不改变官方库。null错误语义、预算/权限与真实RAG适用性均需各自实际运行证据，数据前提核对不能关闭系统门禁。
