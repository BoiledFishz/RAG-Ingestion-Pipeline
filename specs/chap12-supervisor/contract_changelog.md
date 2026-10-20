# Contract / 规则变更日志

版本以 `contracts.py` 中的 `CONTRACT_VERSION` 为准。每条记录说明变更依据（审阅决定或工作单条目）。

| 版本 | 时间 | 变更 | 依据 |
| --- | --- | --- | --- |
| chap12-v1 | 15:54（834cd04） | 初版：六态、汇合规则、DbInput/DbPayload、TrustedContext、预算 150 s / 8 / 4 / 4 / 4 | 实现时自定，无事前审阅 |
| chap12-v1（未改版本号） | 16:58（ab4e8d7） | DbInput 增加 `product_source`、`infer_product`、`query`；DbPayload 增加 `product_source`、`inference_doc_ids`；缺少产品时由 `failed` 改为 `no_data` + `clarification_required` | v2 改进，无事前审阅；本应提升版本号，在 chap12-v2 中补上 |
| chap12-v1（行为变更，字段不变） | P0-2 | RAG 检索按授权产品过滤（检索时，在 RRF 之前）；DB 推断只在授权文档中进行；受限主体追加 limitation | 审阅决定 D3；工作单 P0-2 |
| **chap12-v2** | P0-3 | `CONTRACT_VERSION` 改为 chap12-v2（补上 v2 字段变更的版本号）；`Usage` 增加 `sql_statements`、`local_compute`、`embedding_cache_hits`；预算增加 `sql`（400）和 `local`（16）两个类别 | 审阅决定 D4；工作单 P0-3、P2 |
| chap12-v2 | P2 | `count_documents` 和 `count_by_year` 计数为 0 时返回 **completed**（payload.count=0）；只有 `list_recent_documents` 返回空列表时为 no_data | 审阅决定 D1 |
| chap12-v2 | P1-5 | explain_and_data 的默认数据操作由 `count_documents` 改为 `list_recent_documents`（limit 5），最终回答中作为“相关文档”（doc_id、日期、标题）呈现；data 目标的默认操作仍是计数 | 工作单 P1-5 |
| chap12-v2 | P0-4 | `Usage` 增加 `prompt_tokens`、`completion_tokens`（取自 Ollama 的 prompt_eval_count/eval_count；拿不到时为 null，不记为 0），`tokens` 为两者之和 | 工作单 P0-4 |
| **chap12-v3** | 2026-10-17 第 7 项 | `DbOperation` 增加 `search_product_documents`（产品范围内按问题做 BM25 排序，结果只含该产品、满足过滤条件的文档，空列表为 no_data）；explain_and_data 的默认数据操作改为它；显式 data_request 也把问题文本传给 DB Worker | 调参集研究 `tune/product_study.json`：相关文档含金标 0.469（新）对 0.082（最近文档），n=49 |
| chap12-v3 | 2026-10-17 第 8 项 | `ProductSource` 增加 `model_pick`：问题未写明产品时，模型只能从程序给出的候选列表（授权文档中 BM25 前 10 篇的产品，最多 8 个）中选编号，程序校验编号在列表内且已授权，否则回退规则或要求澄清；顺序（fallback/first）由调参集上的真实模型研究按事先规则决定，未研究前默认 fallback；离线档位不调用模型 | 待办第 8 项 |
| chap12-v3（无结构变化） | 2026-10-19 第五轮 | 新增可选的可回答性核验（`agents/chap12/verifier.py`）：只在真实档位、开启时运行；只能把已发布的 RAG 结果改为 no_data（`invalid_evidence`，limitations 写明“答案核验未通过”），不能新增答案或引用；模型出错或输出无效时保留原答案；调用计入同一请求预算。契约字段不变 | 复盘 retrospective.md 第 1 项 |
| **chap12-v4** | 2026-10-19 第六轮 | `Citation` 增加可选字段 `excerpt`（生成答案时该来源的证据段落，取自 Project 1 trace；无则为空字符串）；向后兼容的新增字段。分级核验用它判断证据是否回答了问题 | tasks.md 第六轮登记 |
