# 比较组件规则最小修订建议（待用户批准）

2026-10-07。原批准规格允许原问题明示组件，既有测试也要求这种合法比较；冻结独立复算只识别产品注册正则，将一题登记为 clarification_required。不能删除原题、修改正例断言或覆盖历史成绩。

拟新增 v0.3.4，仅明确比较槽位的原文字面组件规则与独立复算的新版数据预期：排除URL与API等语法标记；组件与其后32字符内版本关联，不跨下一实体。保留原50条任务/抽样/种子、官方字段、S07、S14、19/6/90预算、权限/非目标和held-out规则；旧版本和旧预期不修改。

独立只读全文库复算：[
  {
    "sample_id": "P2-COMPARE-04",
    "query_sha256": "aa56577c7b571e7431e687936f97ff38b8bd833d0a1a33b8ef9a5f1a4f3cf263",
    "frozen_expectation": {
      "error": "clarification_required:two_entity_version_pairs_missing",
      "predicates": [],
      "counts": [],
      "intersection": null,
      "measurement_complete": false
    },
    "independent_literal_predicates": [
      [
        "ICC",
        "4.0.1"
      ],
      [
        "CPE",
        "5.2.1.2"
      ]
    ],
    "independent_counts": [
      245,
      79
    ],
    "intersection": 2,
    "delta_a_minus_b": 166,
    "status": "proposal_pending_user_approval"
  }
]

证据：component_expectation_proposal_v2.json。第1版误选API为实体的非批准草稿保留为弃用记录；不用于决定。若不批准，保留这一数据/规则冲突，不称核心计数全部通过。
