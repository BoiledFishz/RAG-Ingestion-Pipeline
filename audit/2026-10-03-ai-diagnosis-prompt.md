# TechQA RAG 项目完整结果：给 AI 的诊断提示词

以下内容可整体复制给诊断 AI。最后的逐题矩阵由已保存的原始评测记录生成；如果诊断 AI 能读取仓库，还应结合证据目录检查实际正文和轨迹。

版本提示：主体保留整改前的历史结果快照。2026-10-03后续实验见文末追加记录及
`audit/2026-10-03-quality-diagnosis.md`；例如主体的160项测试不是当前测试总数。
历史全量成绩不得被后续十题小集覆盖或冒充新全量成绩。

---

你是一名负责 RAG、信息检索、Agent 系统和评测方法的资深工程师。请根据以下真实项目结果，诊断未达到要求的部分，提出可以执行和验证的整改方案。先诊断，不要直接替我宣称验收通过。

请严格区分：已观察到的事实、需要代码/原文核验的假设、作业规范缺口、生产质量风险，以及评分方法的局限。没有读到的源码或记录不能声称已检查。不能把流程成功、HTTP 200、Schema 合法、引用 ID 合法或 Critic 通过等同于答案事实正确。

## 1. 项目目标与必须遵守的约束

项目包含同一 Git 仓库中的三个部分：

1. 根项目：生产 Ingestion、Dense/Sparse/Hybrid Retriever、Context Builder、带引用的 RAG API。
2. `enterprise-ai-agent`：Query Rewrite、Retriever Tool、Context Compression、`answer/sources/confidence` 结构化结果。
3. `agentic-rag-homework`：LLM Planner、ReAct Research、Diagnosis/Critic Loop、Single/Multi-Agent 对比。

原作业背景是 AWS 技术支持知识库，但用户已明确要求所有实际流程和评测改为官方 IBM TechQA，禁止合成知识库或伪造黄金问答。不要将用户授权的数据源替换本身当作未完成项。

必须保留以下要求：

| 范围 | 作业要求 |
|---|---|
| Ingestion | PDF/Markdown 混合解析；无法提取文本时自动 OCR；使用 RecursiveCharacterTextSplitter；每块有 source_file/page_number/SHA-256 chunk_hash；每块调用 LLM 生成一句 context_summary；摘要和 Embedding 前查询库内 hash 防止重复计费；单文件坏掉不终止全流程；类型提示、异步批量、logging；clean_text 与空/坏文件 pytest；5 组黄金 QA 的 Ragas Context Recall；256/512 参数表和推荐理由 |
| Dense/Rerank | candidate_k/final_k 可配置；source_file/document_type/language/status 过滤；系统强制 published 不允许覆盖；返回身份/正文/来源/页码/分数/排名；BaseReranker 接口；重排输入 query/text/context_summary；保留召回和重排分数/排名；超时降级；空候选不调用重排 |
| Hybrid | Dense 与 BM25 共享 chunk_id 和过滤；asyncio.gather 并行；手写 RRF；按 chunk_id 去重；融合之后只重排一次；单链路故障仍可降级；保留 dense/sparse/fusion/rerank 排名及来源 |
| Context/生成 | Context Token Budget；同文件最多两块；Final Top-k 后取 Parent；retrieved_context 视为外部数据；关键结论使用来源引用；校验 source_map；空召回/空上下文/校准阈值以下拒答；非法引用修复一次仍失败则拒答 |
| 配置/API/交付 | candidate_k=30、rerank_k=20、final_k=5、RRF 常数60、根 Context 预算8000、每文档2块；POST /v1/rag/query；六类指定检索测试；至少15条分类型黄金问题和 Dense/Dense+Rerank/Hybrid+Rerank 指标；README 架构/公式/数据流/成功及拒答示例；三个阶段 Git Tag；所有项目同一仓库 |
| Agent | Query Rewrite、Retriever Tool、Relevant Context、Structured Output；明确/模糊/不存在三类问题；观察质量与幻觉；Planner 输出 task_id/agent/objective/dependencies 并限制合法 Agent；Research 使用 RAG/Search/Document 工具自主决定继续；Critic 最多重试两次、记录问题及是否解决；比较 Single 与 Supervisor/Specialists 的质量/调用/Token/延迟/失败 |

原题没有提供 F1 或事实准确率的数值及格线。请不要自造“F1 必须达到某数值”的课程评分要求。可另提生产目标，但要注明是建议，并说明如何校准。

所有黄金答案和官方 DOC_IDS 只用于事后评分，不进入 Retriever/Planner/Agent 的输入。允许单元测试用空输入、坏文件、超时/非法输出替身测试故障路径；不允许把这些当作业务评测语料。

## 2. 版本、数据、模型和运行环境

- 结果日期：2026-10-03。
- 仓库：https://github.com/BoiledFishz/RAG-Ingestion-Pipeline
- 分支：`codex/aws-support-ingestion`。
- 整理前已验证的本地/远端提交：`dce773cdb0555a7e6c041de411493b6c9581becd`。
- 当前原生评测的运行源码提交：`3c7def2`；后续 `dce773c` 主要提交结果、文档和检查配置。
- 95 个运行源码文件的快照 SHA-256：`e11acad82cbe1c67f5add432537ba7e2a4ae712314c196b87d72d3badf5217ab`；本轮原生评测期间未变化。
- 官方数据来源：https://github.com/ibm/techqa 指向的 PrimeQA/TechQA 归档。
- 归档 SHA-256：`6b094ef9a69718f727ce8d7e15c4d961e51032cefaa952e0d6af9d176d7ba118`。
- 全量原始记录801,998，有效且唯一文档801,996；空正文2条：`isg3T1016084`、`swg21325092`。
- 全量语义索引3,089,056个 Chunk，文档覆盖、数量和向量有效性检查通过。
- Dense 编码器：`sentence-transformers/all-MiniLM-L6-v2`，384维；revision=`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`。
- Chunk 全部256-token窗口编码，16-token重叠后聚合；Faiss IndexFlatIP，对单位向量精确余弦搜索。
- embedding_id=`8fe17f450ba67b9b0ee7aa9f3a644cb9fd90a1180987ed68f9451b4ba186649b`。
- 默认生成/选择/Planner/Critic：本机 Ollama `qwen2.5:7b`。
- 重排/格式库 Embedding：`nomic-embed-text`；格式 ingestion 摘要：`llama3.2:3b`。
- Qwen 模型摘要：`845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`。
- nomic 模型摘要：`0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`。
- Llama 模型摘要：`a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72`。
- Windows PowerShell；客户端 Python3.14环境 `.venv`，Torch/Faiss Python3.12环境 `.venv312`。
- 内存约14.9GB，RTX3060 Laptop显存6GB；完整Faiss约4.75GB，Chunk SQLite约19GB。不要在在线服务旁再载入一份全量向量；查询编码CPU，为生成模型保留GPU。

这里的“全量”指检索库覆盖全部有效官方文档，不是对每篇文档都人工检查，也不是把每个问答系统都跑完所有数据划分。

## 3. 实际架构及需要诊断的实现边界

默认全库链路：Query → MiniLM Dense / SQLite FTS5 BM25（并行）→ RRF（常数60）→ chunk_id去重 → nomic有限候选重排 → Final Top-k/Parent → Context Compression → 模型选择证据/适用性校验 → 原文正文和引用。

根项目默认30/20/5，预算8000；Enterprise通常Top-8、独立评测Top-10、上下文预算2400、最多8个来源。不要把三个服务的实际参数视为完全相同。

当前全库 `TechQAReranker` 是可解释的复合打分，不是已验证的 Cross-encoder：

```text
semantic = cosine(nomic(query), nomic(context_summary + chunk_text))
lexical = coverage(query, context_summary + chunk_text)
prior = 1 / (1 + bm25_document_rank / 5)
score = 0.50 * semantic + 0.30 * lexical + 0.20 * prior
缺少 bm25_document_rank 时默认1000。
lexical消融模式 = 0.55 * lexical + 0.45 * prior。
重排query实际使用 query[:6000] 并加 search_query 前缀。
```

请评估这个打分及其BM25先验是否使 Dense/Hybrid 不够可比、是否压制语义召回；目前没有证据证明这就是具体失败的根因，必须用消融验证。不要把“换成更大模型/Cross-encoder”写成已经证明有效的修复。

Search Tool 搜索同一个TechQA全库的BM25，Document Tool取同库原文；当前实验没有互联网搜索的独立增益。Agentic正式实验默认仍是RuleRewriter；Enterprise使用真实LLM Rewrite。Agentic可选LLM Rewrite已有保护逻辑，不能将其说成当前所有实验的默认入口。

模型优先选择有限证据ID，由程序渲染原文答案，降低自由生成风险；这可能产生长篇原文、无关标题/链接和步骤不完整问题。确切影响要看逐题正文，不能只凭架构判断。

### 两条 ingestion 路径必须分别验收

1. **格式作业链路**：真实TechQA原文转换成Markdown、文本PDF、扫描PDF；RCTS；OCR；SHA-256幂等；nomic语义Embedding；LLM一句摘要及失败显式降级。这条能力和测试已实现。
2. **全量原生JSON扩展库**：为兼容历史ID，仍使用1200/160的legacy切片，context_summary为官方标题。全量已完成真正MiniLM语义向量，**没有**对3,089,056块全部重新运行RCTS和逐块LLM摘要。

如果要求“全部默认全量流程严格满足上述Ingestion规范”，第二条是明确范围缺口。全量801,996篇不是老师规定的必交数量，而是项目扩展能力；请区分小规模必交能力已实现与扩展链路未全面符合规范。

## 4. 早期验收问题：目前哪些已经处理

| 早期问题 | 当前证据/边界 |
|---|---|
| nomic模型缺失、全量Qdrant未启动 | 当前模型已具备；默认全量语义服务使用Faiss+SQLite，不依赖Docker/Qdrant；真实Dense候选和索引身份验证通过。旧Hash仅显式选择，不能再把“默认Dense还是Hash”当当前问题 |
| 根pytest六个导入错误、Enterprise测试依赖未提交数据、旧API错误断言 | 测试使用已提交官方原文；三个项目独立进程运行；最新共160项通过。不同子项目的api/models/agents同名包仍需隔离，不要同时安装到同一命名空间 |
| Embedding失败却退出0 | 已修复失败阶段计数和非零退出；幂等全部跳过仍属成功；故障路径回归存在 |
| 摘要截断到半个单词 | 已处理完整句校验/显式降级，格式路径测试通过；这不等于全量标题摘要符合LLM要求，也不等于每条真实摘要已人工确认 |
| 重排降级后RRF分数误套语义阈值 | 降级保留检索排序，使用单独覆盖率门控；不比较不同分数空间；保留端到端故障回归 |
| Planner仅返回计划、执行仍固定 | 当前DAG按实际依赖派发；所有最终路径必须经过Diagnosis/Critic；绕过复核的计划须修复，否则阻止发布 |
| sources.quote计入答案评分掩盖正文缺失 | 当前只评正文，引用编号不计分，并加正确文档ID门控；低分和失败继续保留 |
| Agent目录未纳入Git、远端标签未知 | 两个项目及结果已提交/推送；历史Tag远端已核验。Tag是历史阶段，不是当前版本质量签收 |
| PowerShell5把正常logging stderr当异常 | 捕获原生日志期间使用Continue，按实际native退出码判定；控制试验由失败退出1修复为退出0；不修改系统执行策略 |
| 重复构建再次装载完整向量 | 完整索引先校验来源/数量/状态然后复用；约5秒；避免另载一份Faiss/编码器争用内存 |

历史Tag：v1=`c0953d24c4474cb2ffb34c607d6254bde39c43c9`；v2=`70003f2294b7354d1ff952df50085a30a41f73be`；v3=`e2a220e52c3f70e4dde06b0b960e45d8830ba3c3`。对应名称为retriever-v1-dense/retriever-v2-rerank/retriever-v3-hybrid，未强行移动。

## 5. 最新流程与静态验证结果

| 检查 | 当前结果 | 不能由此推断的结论 |
|---|---:|---|
| Enterprise定向真实回归 | 16/16完成，执行异常0，最终invalid_evidence=0 | 不代表当前完整310题达到相同质量 |
| 四种Agent真实实验 | 15题×4=60次，执行异常0、模型异常0 | 不代表正文都解决问题 |
| Planner重复试验 | 10/10有效；非法Agent=0；计划形态1种 | 单一任务/有限样本，不证明所有任务规划稳定 |
| 真实检索证据Critic | 15题×2=30次，跳过0，模型异常0 | 通过率包括批准拒答，不等于事实质量100% |
| 真实HTTP冒烟 | 14项，失败0 | HTTP成功不是答案正确；N题可能在开放库获得答案 |
| pytest | 根55+Enterprise52+Agentic53=160通过 | 控制流/回归通过不能替代全量事实核验 |
| Ruff/Mypy | 全通过；Mypy源码42/28/25 | 无静态错误不等于无逻辑错误 |
| 验收runner | 全阶段完成，退出0 | production_quality_accepted=false |

HTTP覆盖根Dense/Sparse/Hybrid、空过滤拒答、Enterprise，以及RAG/Planner/Research/Single/Multi/Critic。保留一条不阻塞的Starlette/httpx弃用警告。

## 6. 格式 ingestion、Ragas和小型检索结果

官方原文转换14个有效文件全部解析，扫描页自动OCR。512/64产生180个待去重块、178个唯一入库块；再次运行178个hash在摘要/Embedding前全部跳过。必需元数据和hash检查通过。

该历史小库未为每条摘要记录独立provider字段，不能据此追溯每块是否发生过降级。Ragas对照明确使用extractive摘要、真实nomic Embedding、Hybrid+lexical Top-3、Ragas IDBasedContextRecall。

| Chunk Size | Overlap | 唯一Chunk | 5条官方训练QA的Context Recall@3 | 逐题分数 |
|---|---:|---:|---:|---|
| 256 | 32 | 367 | 0.20 | 0,0,0,1,0 |
| 512 | 64 | 178 | 0.40 | 0,1,0,1,0 |

512/64是该子集的推荐，不是全库最优证明；0.40仍偏低。这个Ragas指标是ID命中，不是对每个事实的人工/LLM语义召回判断。

格式库15条官方训练题（12Y/3N），这些阈值在同一子集选择，**不是留出集**：

| 模式 | R@5 | R@10 | MRR | CP@5 | 平均ms | N拒答代理比例 |
|---|---:|---:|---:|---:|---:|---:|
| Dense | .666667 | .833333 | .452877 | .183333 | 931.37 | 1.000000 |
| Dense+Rerank | .583333 | .833333 | .400794 | .116667 | 938.26 | 1.000000 |
| Sparse+Rerank | .500000 | .666667 | .375794 | .100000 | 5.28 | .666667 |
| Hybrid+Rerank | .583333 | .750000 | .393849 | .116667 | 896.75 | .666667 |
| Hybrid+Rerank-outage | .666667 | .833333 | .438988 | .150000 | 880.12 | .333333 |

这些是格式小库历史结果，不能替换下面的全库成绩。2026-09-29旧AWS合成语料成绩不再作为当前TechQA验收证据。

## 7. 全量检索对比及阈值

Train600（450Y/150N）、dev310（160Y/150N）、validation20（11Y/9N）均完成全库检索。只对Y计算下表相关文档指标；每题一个标注文档，R@k是Top-k Chunk是否包含该文档；CP@5是Top-5中该文档Chunk比例；MRR截断在Top-10。

### Train600：阈值校准的检索基础

| 模式 | R@5 | R@10 | MRR | CP@5 | 平均ms |
|---|---:|---:|---:|---:|---:|
| MiniLM Dense | .466667 | .526667 | .376291 | .123111 | 1148.85 |
| Dense+nomic | .531111 | .580000 | .469892 | .161778 | 2539.19 |
| BM25 | .593333 | .628889 | .508829 | .118667 | 2875.78 |
| Hybrid+nomic | .608889 | .671111 | .535258 | .136000 | 3836.15 |

训练曾因本机模型服务退出出现40次请求失败；恢复只重跑失败/未完成题，最终canonical600条错误0；641次历史尝试仍保留。最终summary有resume/reuse字段，不能说从未失败或每次运行都重新测600题。

### Dev310：全量语义检索

| 模式 | R@5 | R@10 | MRR | CP@5 | 平均ms |
|---|---:|---:|---:|---:|---:|
| MiniLM Dense | .493750 | .568750 | .392411 | .127500 | 1221.85 |
| Dense+nomic | .612500 | .631250 | .496466 | .175000 | 2522.20 |
| BM25 | .637500 | .681250 | .516466 | .127500 | 3045.06 |
| Hybrid+nomic | .650000 | .693750 | .549660 | .140000 | 3428.34 |

### Validation20：与dev重叠，不是独立盲测

| 模式 | R@5 | R@10 | MRR | CP@5 | 平均ms |
|---|---:|---:|---:|---:|---:|
| MiniLM Dense | .636364 | .636364 | .484848 | .163636 | 919.05 |
| Dense+nomic | .727273 | .727273 | .545455 | .218182 | 957.72 |
| BM25 | .636364 | .727273 | .588745 | .127273 | 2778.42 |
| Hybrid+nomic | .727273 | .727273 | .553030 | .145455 | 2836.29 |

运行错误均为0。共享桌面、缓存和并行检查影响延迟，不是隔离性能基准。严格文档ID评分会把其他同样有用的官方文档记为未命中。

### 历史Hash全库dev基线，仅供对照

| 模式 | R@5 | R@10 | MRR | CP@5 | 平均ms |
|---|---:|---:|---:|---:|---:|
| Hash Dense | .131250 | .143750 | .09652 | .026250 | 599.2 |
| Hash Dense+nomic | .156250 | .168750 | .14074 | .035000 | 2032.3 |
| BM25 | .637500 | .681250 | .51647 | .127500 | 3138.3 |
| Hybrid+nomic | .643750 | .675000 | .54709 | .128750 | 4214.5 |

真实语义Dense R@5提升36.25个百分点；Hybrid仅从.64375到.65000。不能把Dense增幅当Hybrid增幅，不能把Hash当成熟语义基线。

### 当前阈值：仅使用Train600，不是置信度

| 门控 | 阈值 | 训练balanced accuracy | Y接受代理比例 | N拒答代理比例 |
|---|---:|---:|---:|---:|
| Dense+Rerank | .5569678087 | .5577778 | .5888889 | .5266667 |
| Hybrid+Rerank | .6555182696 | .5533333 | .7933333 | .3133333 |

Agent候选下限=.4255663794，是训练已观察到的377个相关Top-10候选最低分，conditional retention=1.0。这不代表训练所有Y都召回、不代表答案概率、不代表N在全库无答案。

## 8. Enterprise问答：完整旧版与当前回归必须分开

### 已归档的完整310题，Qwen2.5:7b，真实全链路

| 指标 | 初次语义版本techqa_semantic | 适用性复核版techqa_semantic_v3 |
|---|---:|---:|
| Y正文F1×正确文档引用 | .2134057740 | .2130310860 |
| Y接受率 | .82500 | .78750 |
| N拒答标签代理比例 | .0733333 | .1000000 |
| R@5 | .60000 | .60000 |
| R@10 | .63750 | .63750 |
| MRR | .4947644 | .4963269 |
| 平均端到端ms | 12168.09 | 15824.94 |
| 执行异常 | 0 | 0 |

v3状态为238answered、43clarified、27unanswerable、2invalid_evidence。DEV_Q113/236一次修复后仍失败；不把输出验证失败记作拒答成功。Dense/Sparse异常降级日志为0。

这两列是旧代码，不是当前整改代码的完整成绩。当前完整310题尚未重跑；不能用当前16题分数与旧310题分数直接宣称质量提高。

另有2026-09-30历史开放全库offline/extractive Enterprise310：R@5=.64375，R@10=.675，MRR=.54709，N代理=.380，平均6499.2ms，执行错误0；使用旧Hash Dense+nomic，不是310题全LLM，不与当前模型成绩直接等同。

### 当前16题定向回归，真实全库+Qwen，未续用任何旧答案

官方dev逐字复制：DEV_Q000–013、113、236；8Y/8N。4条已知失败+原始顺序12条其他题；开发回归，不是盲测。12篇小文档快照只供离线测试，原生回归实际检索全部801,996篇。

| 指标 | 旧v3相同16题子集 | 当前techqa_remediation_v4 |
|---|---:|---:|
| Y正文F1×正确文档引用 | .4295041344 | .4618782351 |
| Y接受率 | .875 | .875 |
| N拒答代理比例 | .250 | .125 |
| 澄清 | 2 | 0 |
| 最终invalid_evidence | 2 | 0 |
| 执行异常 | 0 | 0 |

当前R@5=.875、R@10=.875、MRR=.6354167；平均16769.81ms；14answered、2unanswerable。N代理下降，不能声称拒答已改善。

## 9. Agentic四版本与Critic：最新真实结果

15条固定官方训练题（12Y/3N），各版本检索同一全库，共60次；不存在合成评测或模拟模型代替真实质量实验。

| 指标 | Fixed | ReAct | Single | Multi |
|---|---:|---:|---:|---:|
| Y正文F1×正确文档引用 | .252169 | .243931 | .243931 | .208098 |
| N标签拒答代理比例 | .000000 | .000000 | .000000 | .333333 |
| 全15题混合质量代理分 | .201736 | .195145 | .195145 | .233145 |
| 平均LLM Calls | 1.400 | 3.467 | 3.467 | 6.600 |
| 平均Tool Calls | 3.000 | 1.800 | 1.800 | 1.933 |
| 平均Token估算 | 1918.87 | 5579.47 | 5632.20 | 8216.60 |
| 平均Latency ms | 8938.24 | 14630.48 | 12514.54 | 30862.32 |
| 严格Failure Rate | 1.000 | 1.000 | 1.000 | .933333 |
| 执行/模型异常 | 0/0 | 0/0 | 0/0 | 0/0 |
| fallback/最终Critic拒绝计数 | 0/0 | 0/0 | 0/0 | 0/0 |

混合质量分包含N标签拒答分，故Multi全题分较高不代表其Y正文更好。严格Failure Rate定义为正文质量未满分或异常，不是崩溃率、不是人工事实错误率。Token是正则估算，不是模型tokenizer或计费Token。

此前同15题语义版本：Fixed/ReAct/Single Y正文F1均.189122，Multi=.153289；LLM Calls分别1.667/4/4/8.133；Token约2130/5963/5957/9998；N代理前三者0，Multi=.333333；执行错误0。去掉正确文档门控后Single F1约.22666、Multi约.16054，仍低。旧Fixed延迟含一次20分钟以上共享桌面阻塞，不做新旧性能提升证明。

更早Llama3.2:3b+Hash全库15题：全题混合质量Fixed/ReAct/Single=.1010、Multi=.0945；调用0/2/2/4.8；Token0/1761.2/1758.9/4371.7；延迟3487.7/3641.3/2688.9/9938.6ms；严格失败率约.933，执行错误0。模型、向量、实现及指标范围都有差异，不适合单变量归因。

Planner当前10次Schema/DAG有效1.0，非法Agent0，计划形态1种；真实计划驱动执行。analyst/report_writer是保留原文证据的确定性专家；research/diagnosis/critic使用LLM，不要假定所有节点都调用模型。

### Critic正式重复实验

15题全库实际检索Top-20后，为每题固定证据、重复两次，共30次；没有向模型传黄金答案或DOC_IDS，没有空证据跳过。

| 指标 | 旧正式语义版本 | 当前定向整改版本 |
|---|---:|---:|
| 最终复核通过率（含批准拒答） | 1.0000 | 1.0000 |
| 充分性/最终诊断一致性 | 1.0000/1.0000 | 1.0000/1.0000 |
| 首次复核通过率 | .8000 | .8667 |
| 平均Retry | .2000 | .1333 |
| Y接受率 | .5000 | .5000 |
| Y正文F1×正确文档引用 | .1665406 | .1406214 |
| N标签拒答代理比例 | .333333 | .333333 |
| 模型错误/跳过 | 0/0 | 0/0 |

当前全题答案接受率=.533333。Critic稳定了，但Y正文指标下降，不允许据稳定性/通过率签收生产质量。

## 10. 具体失败或有疑问的案例

请优先逐案分析，区分“目标文档没有召回”“召回正确但段落选错”“段落充分但正文组织不好”“复核误判”和“评分代理不准”。

### DEV_Q000：安装问题被相似回滚/旧安装文档干扰

原问题：安装Web GUI8.1FP7；IM1.8报告已装DASH3.1.0.3，但要求DASH3.1.2.1或更高。

官方目标文档=`swg24042191`，参考答案描述Jazz for Service Management1.1.3.0是完整刷新版本；正确解决内容需要回到原文核验，不能仅凭参考短句推断全部操作步骤。

历史错误选择：`swg21960632`控制台CLI回滚问题；加操作冲突过滤后又选`swg21681385`较旧8.1.0安装前提（最低3.1.0.3）。当前显式同产品最低版本前提检查移除旧条件，最终无来源安全拒答。

当前10个候选文档：swg21960632、swg22011877、swg21963295、swg21967886、swg21681385、swg24039724、swg21679259、swg24043825、swg24043504、swg21960630。目标文档不在Top-10；R@5/R@10=0。**错误被挡住，但问题仍未解决。** 请检查目标是否在Dense/BM25候选30、RRF和重排哪个环节消失，而不是直接降低发布门槛。

### DEV_Q007：正确Gateway文档已选中，但比较结论不足

原问题：Netcool Omnibus/NOI该用哪个Socket Gateway？比较`nco-g-socket-java-2_0`与`nco-g-socket-10_0`。

旧版多余追问部署版本；早期整改误用`swg21970417` Socket(Java)Probe。当前Rewrite保护包名、Gateway/Probe冲突过滤后选择`swg21625776`官方Gateway版本发布文档。

实际正文主要为：Gateway发布标题、2015-08-06新版本可下载、Knowledge Center指南和Passport Advantage安装包链接，带[S1]。正文F1=.2589928。不是完整清晰的“两种包如何选”的回答，且标题/链接冗长。不要仅因文档ID正确判为已解决；需要检查原文是否包含比较事实、是否检索了补充文档。

### DEV_Q113：WAS7 HTTPS，校验修复成功但不代表完整答案

问题：Rule Team/Execution Server在WAS7.0上HTTPS连接，设置`ilog.rules.res.allowSelfSignedCertificate=true`后仍SSLHandshakeException。

当前引用`swg21427447`，正文说Solution A：将服务器证书加入客户端JVM truststore，默认HTTPS仅接受可信证书；文档说有两种方案，但当前正文只给其中第一种简述，步骤完整性需要复查。

首次适用性复核提出source_claim=`WebSphere Application Server V7.0`，该字串不在S1，程序拒绝并给实际字段/来源的精确诊断；一次修复后发布。trace.validation_failures仍保留首次错误。

原标签N表示原始候选范围无标注答案；开放库有该文档，不能把接受率当幻觉率，也不能把本题当前回答记为拒答改善。

### DEV_Q236：API Connect安全公告，需要事实核验

问题要求API Connect所涉及CVE-2016-5546/5548/5549/5547/2183及CVE-2017-3511公告信息。

当前全库引用`swg22006126`[S5]，选择受影响版本/修复表：APIConnect5.0.0.0–5.0.6.2→5.0.6.3，5.0.7.0–5.0.7.2→5.0.8.0，APAR LI79749及Fix Central链接。页脚通知已过滤、原文校验通过。

原标签N，选中文档不属于原题DOC_IDS；不能修改标签抬分。请核验当前选中的公告是否覆盖问题全部CVE、适用版本和修复，不要仅因表格/引用合法宣称完整正确。

### TRAIN_Q007：BPM/MQ权限题引用泛化的迁移说明

正确标注文档=`swg21636093`。当前Single/Multi选`swg21138961`和`swg21691988`，正文描述WAS7/8迁移8.5的JMS默认用户变化、MQ2035权限错误，以及认证别名/user.name条件。严格文档门控分0，去掉门控正文F1仍约.16555。

这些内容可能有局部相关性，但未证明回答了原BPM问题。请同时看正确文档和引用原文，不要把所有0分归因ID门控。

### TRAIN_Q011：SPSS25新电脑，许可片段不等于完整安装指导

Single引用`swg21985888`第2步：新电脑许可授权码、许可次数耗尽处理链接、创建/确认授权码，末尾“Complete”；没有完整安装解决过程。Multi直接拒答，两个版本严格质量分均0。

Single摘录是实际许可文档内容，不能直接说所有事实虚构；主要检查是否漏前置安装步骤/问题范围不匹配/正确目标未召回，以及Multi是否过度拒答。

### TRAIN_Q006：Critic重复一致但正文质量下降

旧/当前重复1的正文F1约.8080→.103774；正文895→615字符。证据选择从漏洞描述变化为受影响产品/版本/条件片段，需对照完整原问题和参考原文人工判定是否覆盖主问、遗漏事实或只是词汇重叠变化。不能说下降只是答案变长（实际更短）。

作为对照，TRAIN_Q001重复1 F1约.434389→.827586，但当前正文仍有大量原始列表星号、重复代码片段；高分也不代表呈现质量优秀。TRAIN_Q000正式Single/Fixed正文出现重复streamtool步骤，适合检查去重与指令呈现。

### 其他已观察到的旧错误

UrbanCode问误用DataStage操作、SPSS症状3误用症状5补丁，推动了适用性独立复核；DEV_Q011命中另一个jextract APAR。它们属于历史失败，不能仅凭当前16题无校验错误认定全局已全部解决。

## 11. 已做的整改和失败实验，避免重复无效路径

当前已做：包名/API/CVE/数字/否定保护；可检索具体标识先检索而非澄清；完整Parent段落边界；普通900字符RCTS证据片段，遇指令组可扩到1800，完整组装不下则跳过；序列化预算继续生效；官方原文精确子串校验；安装/回滚、Gateway/Probe、同产品较旧最低版本错误前提过滤；独立适用性复核；一次结构/引用修复带实际失败字段和合法ID；Critic反馈记录来源及具体冲突；最多2次Critic Retry。

这些有限规则尚不覆盖所有产品、隐含条件、版本范围、缺失步骤和来源误选。未知关系不能假装已经理解。版本tuple对3.1与3.1.0.0的规范化是值得核验的代码边界，当前具体案例尚未证明因此失败。

历史Enterprise复核回放固定旧检索和初始答案，**没有**重跑Rewrite/Retriever：

| 回放版本 | Y正文F1 | Y接受率 | N标签代理比例 | 错误/边界 |
|---|---:|---:|---:|---|
| review_v1 | .142533 | .38750 | .526667 | 过度拒答；执行错误0 |
| review_v2 | .122922 | .31875 | .566667 | 更严重拒答；错误0 |
| review_v3 | .000000 | .00625 | .833333 | 246模型试验拒绝245；未采用 |
| review_v4 | .145840 | .54375 | .233333 | 引文/校验错误33 |
| review_v5 | — | — | — | 57/310后中断，非完整结果 |
| review_v6 | .212796 | .80625 | .126667 | 完整310回放，错误1；不是新全链路成绩 |

这证明盲目提高拒答或收紧Critic可能牺牲Y覆盖；不能把N比例增加当答案质量改善。

整改中原生16题：remediation_v1完整但仍错用Probe；Y F1=.429504、Y接受=.875、N代理=.125。v2完整但仍接受较旧安装前提；F1=.461878、Y接受=1.0、N代理=.125。v3首题前因PowerShell日志重定向中断（0/16），只有interrupted.json，没有完整summary。v4修正并从头运行；成绩见上。相同F1不表示v2的错误安全性已正确。

旧Enterprise全链路semantic_v2仅13题，停止旧代码后从头写v3。早期Agentic语义v1有TRAIN_Q005绕过复核的Planner路径失败，修正后完整重跑60次。上述中间轨迹均保留。

Critic开发5条Y实际检索实验，v3 F1=.2381/Y接受=.50/充分性一致=.80，v4 F1=.3997/Y接受=.60/两次充分性与诊断一致1.0/模型错误0；这是开发子集，不是正式15题签收。更早曾出现Critic通过100%但充分答案仅10%，因此必须同时报告充分答案覆盖和拒答。

## 12. 请交付的诊断结果与可验证整改计划

请按以下顺序输出，用具体证据而不是通用建议：

1. **验收矩阵**：每项标记“已实现且有运行证据 / 有实现但证据范围不足 / 明确规范缺口 / 生产效果未证实 / 仅历史问题已处理”。不要把原题未要求的数值目标当作课程必交。
2. **问题优先级表**：问题、证据/案例ID、所属环节、已确认事实、根因假设及可信度、最小修改、预计收益、可能回归、实施成本。列出最值得先改的3项。
3. **逐案定位实验**：DEV_Q000、DEV_Q007、TRAIN_Q007、TRAIN_Q011、TRAIN_Q006分别设计可区分召回/重排/压缩/生成/Critic/评分的实验，明确读取字段与判断标准。
4. **检索消融**：原始query与rewrite；Dense/BM25各Top-30及目标文档rank；RRF前后；复合重排三个分量；去BM25 prior或变权重；有限候选上限变化；是否需要真正Cross-encoder。先小规模原题，再固定配置全评，不把docID或答案塞进query。
5. **答案与证据方案**：如何保留完整步骤、条件、版本和主问题答案，减少原文噪声/重复/链接；原文选择与受控摘要如何兼顾事实/简洁；如何防止有效原文被错误组合或用于错误问题；给可以实现的输入输出/校验设计。
6. **Critic有效性实验**：不仅测重复一致，还测事实缺陷识别、误拒答、反馈是否修复、每轮新增/遗留问题；比较无Critic/当前Critic/改进Critic，最多2次Retry；防止共享模型互相认可同一错误。
7. **评测整改**：保持原始N标签与旧指标；另做基于真实官方问题和全文档的人工全库可回答性/事实/步骤标注，区分检索不足和真正无答案；正文F1/文档ID指标与人工事实分并列，不改旧标签抬分；规划独立不重叠的留出题、误差条/样本限制、实际tokenizer预算验证。
8. **全量Ingestion规范补齐**：判断是否需要另建RCTS+逐块LLM摘要索引；给兼容chunk_id/稀疏索引/哈希幂等/断点/数据来源的迁移方案、数量级成本估算与小规模先验实验。不能要求在当前14.9GB机器同时载两份全量Faiss。
9. **执行与复验顺序**：先最小官方失败案例→固定源码/数据/模型/协议→完整dev310新全链路→正式Agent60/Critic30→必要的新留出评测。不同源码不能续跑同一检查点；保留旧失败，结果目录不覆盖。
10. **结论**：哪些结果足以支持作业功能提交，哪些还不支持生产发布；每个结论写出可用证据和缺少的证据。Multi-Agent是否值得保留，按质量收益/覆盖/成本判断，不能预设更好。

如果不能访问仓库，只给由上述事实支持的诊断和待核验项；需要资料时具体列出文件/题号/字段，不编造函数行为、准确率或修复后的成绩。如果你可以访问源码，先读原始记录和关键代码再下结论。此提示词要求诊断，不授权删除数据、覆盖旧结果、改标签或发布未经验证的改动。

## 13. 原始证据及源码索引（路径相对仓库根）

优先读取：

- `audit/2026-10-03-targeted-remediation.md`：最新主报告。
- `audit/2026-10-02-semantic-agent.md`：全量语义/完整旧问答/失败回放。
- `audit/2026-09-30-techqa.md`：迁移、格式路径与旧Hash对照。
- `audit/techqa_remediation_v4_environment.json`、`techqa_remediation_v4_validation.json`：源码快照、模型、流程范围。
- `audit/techqa_remediation_v4_comparison.json`：相同16题的新旧对比。
- `audit/2026-10-03-remediation-source.json`：16题/12篇原文逐项核验。
- `evals/techqa_source_inventory.json`、`techqa_semantic_manifest.json`、`techqa_semantic_models.json`：来源及索引/模型身份。
- `evals/techqa_ragas_results.json`、`techqa_fixture_retrieval.json`、`techqa_ingestion_verification.json`：格式库结果。
- `evals/techqa_semantic_calibration/`、`techqa_semantic_full/`、`techqa_semantic_validation/`：600/310/20题summary、逐题runs.jsonl及attempts。
- `config/techqa_thresholds.json`：训练阈值及其定义。
- `enterprise-ai-agent/evaluation/results/techqa_semantic/`、`techqa_semantic_v3/`：完整旧版310题summary/runs/run_config。
- `enterprise-ai-agent/evaluation/results/techqa_remediation_v4/`：当前16题summary/runs/run_config。
- `enterprise-ai-agent/evaluation/results/techqa_semantic_review_v1`至`v6`、`techqa_remediation_v1`至`v3`：中间失败/部分运行（有些不存在完整summary）。
- `agentic-rag-homework/evaluation/results/techqa_remediation_v4/`：当前Agent60、Planner10、报告、逐题正文/DAG/反馈。
- `agentic-rag-homework/evaluation/results/techqa_remediation_v4_critic/runs.jsonl`、`summary.json`：当前Critic30。
- `agentic-rag-homework/evaluation/results/techqa_semantic/`、`techqa_semantic_critic_retrieved/`、`techqa_critic_development/`：旧正式/开发对照。
- `evals/techqa_remediation_v4_api_smoke.json`：真实HTTP请求及响应。
- `audit/techqa_remediation_v4_pytest.txt`及同前缀各阶段log：160测试及运行日志。

关键实现：

- `src/rag/techqa/retrieval.py`：legacy_chunks、Dense/BM25、复合Reranker、共享Pipeline。
- `src/rag/techqa/semantic.py`、`embedding_server.py`：真实编码、构建/复用、在线查询。
- `src/rag/techqa/query.py`：保护词、操作/组件/版本前提冲突规则。
- `src/rag/techqa/evidence.py`：段落/指令组、Parent边界、优先解答片段。
- `src/rag/ingestion/{pipeline,providers,chunking,utils,cli,vector_store}.py`：格式作业链路。
- `src/rag/retrieval/{fusion,pipeline,context_builder,relevance}.py`及`generation/service.py`：RRF、预算、门控、降级与引用。
- `enterprise-ai-agent/agents/rag_agent/{rewrite,compression,generation,service}.py`：当前Enterprise实际逻辑。
- `enterprise-ai-agent/evaluation/evaluate.py`：正文/文档门控及检查点。
- `agentic-rag-homework/agents/{planner,research,critic,systems}.py`及`agents/rag_agent/service.py`：实际任务执行/证据/复核。
- `agentic-rag-homework/evaluation/{factory,run,critic_stability,sufficiency}.py`：正式实验与评分。
- `scripts/run-remediation-checks.ps1`：新目录、不覆盖、独立阶段退出判定。

本机原文/全量数据库位于Git忽略目录；GitHub单独链接不保证诊断AI能看到它们。当前小型官方fixture和regression已提交；需要全文档时应按README获取同一归档并校验来源。不要把看不到的全量文件当作已核验。

复现入口：

```powershell
./scripts/start-local.ps1 -FullTechQA
python scripts/prepare_techqa_regression.py
./scripts/run-remediation-checks.ps1
python scripts/test_all.py
```

完整当前Enterprise310题计划输出新目录`enterprise-ai-agent/evaluation/results/techqa_semantic_v4`，目前尚无完整新成绩；`run-semantic-acceptance.ps1`可按其README说明执行。不得用旧v3或新16题冒充。

## 14. 逐题结果矩阵

下列矩阵直接取自当前已保存的原生评测结果；Y/N保留官方标签。N栏质量分即使为0也不能推断答案事实错误，仍需考虑开放全库范围。实际完整正文和工具轨迹在上述runs记录中。

### 14.1 当前Enterprise16题

| ID | 标签 | R@5/R@10 | Y正文F1 | 状态 | 发布来源 | 校验失败历史条数 |
|---|---|---|---:|---|---|---:|
| DEV_Q000 | Y | 0/0 | 0.000000 | unanswerable | 无 | 0 |
| DEV_Q001 | N | —/— | — | answered | swg21968787 | 0 |
| DEV_Q002 | Y | 1/1 | 1.000000 | answered | swg21978390 | 0 |
| DEV_Q003 | N | —/— | — | unanswerable | 无 | 0 |
| DEV_Q004 | N | —/— | — | answered | swg21480755 | 0 |
| DEV_Q005 | N | —/— | — | answered | swg1IC95983 | 0 |
| DEV_Q006 | N | —/— | — | answered | swg1PI25634 | 0 |
| DEV_Q007 | Y | 1/1 | 0.258993 | answered | swg21625776 | 0 |
| DEV_Q008 | Y | 1/1 | 0.297030 | answered | swg21412061 | 0 |
| DEV_Q009 | N | —/— | — | answered | swg21636650 | 0 |
| DEV_Q010 | Y | 1/1 | 0.705882 | answered | swg21317981 | 0 |
| DEV_Q011 | Y | 1/1 | 0.000000 | answered | swg1IV25299 | 0 |
| DEV_Q012 | Y | 1/1 | 1.000000 | answered | swg21959723 | 0 |
| DEV_Q013 | Y | 1/1 | 0.433121 | answered | swg24037227,swg21665766 | 0 |
| DEV_Q113 | N | —/— | — | answered | swg21427447 | 1 |
| DEV_Q236 | N | —/— | — | answered | swg22006126 | 0 |

### 14.2 当前Agent15题×4版本

分数是正式评测的逐题quality：Y为正文F1×正确文档门控，N为原标签拒答代理分。表内每行四版本均为原生完成，error为空；来源仅列Single/Multi实际输出。

| ID | 标签 | Fixed | ReAct | Single | Multi | Single来源 | Multi来源 |
|---|---|---:|---:|---:|---:|---|---|
| TRAIN_Q000 | Y | 0.756098 | 0.756098 | 0.756098 | 0.756098 | swg21996508,swg1IT18432 | swg21996508,swg1IT18432 |
| TRAIN_Q001 | Y | 0.827586 | 0.827586 | 0.827586 | 0.827586 | swg21675316 | swg21675316 |
| TRAIN_Q003 | Y | 0.809717 | 0.809717 | 0.809717 | 0.809717 | swg21670474,swg21179559 | swg21670474,swg21179559 |
| TRAIN_Q005 | Y | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 无 | 无 |
| TRAIN_Q006 | Y | 0.103774 | 0.103774 | 0.103774 | 0.103774 | swg22008493,swg22008493 | swg22008493,swg22008493 |
| TRAIN_Q007 | Y | 0.000000 | 0.000000 | 0.000000 | 0.000000 | swg21138961,swg21691988 | swg21138961,swg21691988 |
| TRAIN_Q008 | Y | 0.098859 | 0.000000 | 0.000000 | 0.000000 | swg27021665 | 无 |
| TRAIN_Q009 | Y | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 无 | 无 |
| TRAIN_Q010 | Y | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 无 | 无 |
| TRAIN_Q011 | Y | 0.000000 | 0.000000 | 0.000000 | 0.000000 | swg21985888 | 无 |
| TRAIN_Q012 | Y | 0.000000 | 0.000000 | 0.000000 | 0.000000 | swg21407889,swg21413459 | 无 |
| TRAIN_Q013 | Y | 0.430000 | 0.430000 | 0.430000 | 0.000000 | swg21618719 | 无 |
| TRAIN_Q002 | N | 0.000000 | 0.000000 | 0.000000 | 1.000000 | swg21225022,swg21225022 | 无 |
| TRAIN_Q004 | N | 0.000000 | 0.000000 | 0.000000 | 0.000000 | swg22013692 | swg22013692 |
| TRAIN_Q021 | N | 0.000000 | 0.000000 | 0.000000 | 0.000000 | swg22010311,swg22011754 | swg22010311,swg22011754 |

### 14.3 当前Critic15题×2重复

两次均为reviewed/最终passed=true。充分回答false的通过意味着批准拒答；不能当作事实回答正确。正文F1是保存记录的body_f1。

| ID | 标签 | 正文F1重复1 | 正文F1重复2 | 充分回答1/2 | Retry1/2 |
|---|---|---:|---:|---|---|
| TRAIN_Q000 | Y | 0.756098 | 0.756098 | True/True | 0/0 |
| TRAIN_Q001 | Y | 0.827586 | 0.827586 | True/True | 0/0 |
| TRAIN_Q003 | Y | 0.000000 | 0.000000 | False/False | 1/1 |
| TRAIN_Q005 | Y | 0.000000 | 0.000000 | False/False | 0/0 |
| TRAIN_Q006 | Y | 0.103774 | 0.103774 | True/True | 0/0 |
| TRAIN_Q007 | Y | 0.000000 | 0.000000 | True/True | 0/0 |
| TRAIN_Q008 | Y | 0.000000 | 0.000000 | False/False | 0/0 |
| TRAIN_Q009 | Y | 0.000000 | 0.000000 | False/False | 0/0 |
| TRAIN_Q010 | Y | 0.000000 | 0.000000 | False/False | 0/0 |
| TRAIN_Q011 | Y | 0.000000 | 0.000000 | True/True | 1/1 |
| TRAIN_Q012 | Y | 0.000000 | 0.000000 | True/True | 0/0 |
| TRAIN_Q013 | Y | 0.000000 | 0.000000 | False/False | 0/0 |
| TRAIN_Q002 | N | 0.000000 | 0.000000 | False/False | 0/0 |
| TRAIN_Q004 | N | 0.000000 | 0.000000 | True/True | 0/0 |
| TRAIN_Q021 | N | 0.000000 | 0.000000 | True/True | 0/0 |

请现在依据上述证据开始诊断。先给出最重要的判断，再给出可执行的优先整改和验证实验；不要重复一遍报告，也不要把未经验证的猜测写成结论。


## 追加：2026-10-03本轮整改的已完成实验

请先读 `audit/2026-10-03-quality-diagnosis.md` 与根因目录。四个独立提交分别加入排序不变的诊断、两个互补原文片段、实际正文事实/逐issue验证、保持默认权重的重排参数化。目标文档ID只用于事后诊断，未输入Agent。

同一个官方失败五题+成功五题集，均在完整语义库开放检索，Qwen2.5:7b原生调用，各10题均为Y：

| 实验 | R@5/R@10 | MRR | 正文F1×正确文档 | 有来源回答 | 平均延迟ms |
|---|---:|---:|---:|---:|---:|
| controlled claims + fact audit (03) | .7/.7 | .6333 | .1068 | .4 | 64199 |
| extractive + fact audit (04) | .7/.7 | .6333 | .3431 | .6 | 27756 |
| same-document extractive + audit (05) | .7/.7 | .6333 | .4375 | .9 | 28759 |
| principal/option/command/steps checks (06) | .7/.7 | .6333 | .4188 | .6 | 75074 |

这些是不同代码的开发实验，不能推断全局性能或稳定性。无N样本，N拒答代理不可估计。06未复用checkpoint且源码/数据/阈值/索引manifest前后相同，执行异常0。它拦截了DASH查询补丁级别和MQ泛配置误答，CVE完整保留条件；但Socket仍拒答、SPSS缺具体步骤，原成功对照P8出现误拒，正文有格式噪声。自动审阅不是独立事实真值。AI六项评分与未评分的人工表位于 `audit/techqa_factual_review_20261003-02/`。

Critic首轮同源10例×3版本：NoCritic defect recall0/false accept1；旧版 .625/.375、false reject0；初始事实版 .375/.625、false reject0。第二轮新版完整10例加命令/步骤守卫：.875/.125、false reject .5（1/2），调用6.4、估算token8131.5、延迟84917ms。第三轮症状/合理拒答两个案例针对性复验：检出1/1、误接受0/1、误拒0/1，不能拼成完整十例成绩。每次最终修复的独立事实评分仍未完成，repair/new-issue/coverage为null。

后续又加入限定在原文受影响版本表的逐行条件守卫：另一版本的条件不能证明本版本。原始完整公告必须仍通过；自由paraphrase未被这个确定性规则全面覆盖。06是在该最后守卫之前运行，须分别读取后续组件实验，不能回填06指标。

真实Ingestion试验已按文档ID的SHA抽取2,000原始文档，legacy8718/RCTS8982块，8736唯一hash；最先20块实际LLM摘要成功20、失败0、平均1442ms、中位1121ms。完整摘要、B索引与A/B收益未完成，不可宣称全库迁移达标。全量3,089,056块仍为legacy/title，服务未覆盖旧索引。

生产实验功能保持显式开关：TECHQA_GENERATION=controlled、TECHQA_FACT_AUDIT=1；默认extractive和audit=0。没有降低阈值来抬分，没有移动旧标签。

当前Phase4门槛失败，不进入Phase5生产冻结/Phase6 dev310、Agent60、Critic30新全量复验；这些是Not yet verified。请集中诊断P8误拒、SPSS步骤不足、条件遗漏及格式噪声，不要把源码测试通过等同于生产事实质量通过。


### 追加的完整检测与最终默认入口

Critic组件04在同一十例开发集初次检测8/8缺陷、接受2/2正确对照，初次无协议错误；平均6.9调用、9054.5估算token、87272ms，4个修复过程出现协议/校验错误，8个缺陷最终未通过Critic。不能用这一次组件成绩宣称生产修复有效。04还在条件仍缺失时误标该issue resolved，因此后续代码重做修复证明，并保留累计未解决issue。

修改后组件05仅两个缺陷：初次检出2/2，第三轮仍验证首轮事实issue及第二轮协议issue，未再误标删条件修复；两个过程仍有校验错误并耗尽两次重试，平均7调用、8488估算token、97436ms。无正确对照，false reject=null。不能与04其余八题拼成新完整成绩。

最终已提交代码的默认入口（07，extractive、fact audit=0）完成10题：R@5=.7、R@10=.7、MRR=.6333、正文F1×文档门控=.43812856、有来源回答=.8、平均20799ms、执行异常0。P8回答恢复，Oracle题却拒答；Socket只答V8.1、MQ只给诊断跟踪、SPSS只给笼统许可操作。五个成功控制仍只答四个，Phase4未通过。没有独立人工事实评分或新全量成绩。

源码提交：0582605实验受控生成/协议保护；2112845累计Critic issue及修复证明；1fda5bb隔离Ingestion试验。当前192项pytest通过（81+52+59），Ruff/Mypy通过。06、Critic04、Critic05/Enterprise07完整Python源码ZIP及与运行协议一致的SHA位于audit/techqa_source_snapshots_20261003-01；03/04/05较早Enterprise实验只有哈希和轨迹，没有完整源码字节快照，不能声称可精确重现。

请把完整检测收益、修复失败、误拒、资料本身不完整和评分偏差分别分析。生产发布仍Not supported；新dev310/Agent60/Critic30、独立人工评分、完成2k摘要及A/B收益均Not yet verified。旧结果和旧标签指向保留。
