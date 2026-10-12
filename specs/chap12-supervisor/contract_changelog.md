# Contract / 规则变更日志

版本以 `contracts.py` 中的 `CONTRACT_VERSION` 为准。每条记录说明变更依据（审阅决定或工作单条目）。

| 版本 | 时间 | 变更 | 依据 |
| --- | --- | --- | --- |
| chap12-v1 | 15:54（834cd04） | 初版：六态、汇合规则、DbInput/DbPayload、TrustedContext、预算 150 s / 8 / 4 / 4 / 4 | 实现时自定，无事前审阅 |
| chap12-v1（未改版本号） | 16:58（ab4e8d7） | DbInput 增加 `product_source`、`infer_product`、`query`；DbPayload 增加 `product_source`、`inference_doc_ids`；缺少产品时由 `failed` 改为 `no_data` + `clarification_required` | v2 改进，无事前审阅；本应提升版本号，在 chap12-v2 中补上 |
