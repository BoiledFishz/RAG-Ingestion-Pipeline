# Project 2 当前机器证据详情

旧LLM评分作废，不引用一致率。

```json
{
  "spec_version": "v0.3.2",
  "generated_at": "2026-10-07T02:22:02.487149+00:00",
  "execution_status": "stopped_frozen_active_execution",
  "current_stage": "Chap13",
  "stop_reason": "累计执行期限37.941018秒耗尽，恢复仍为RAG timeout/DB completed→partial；停机已排除。根因属于冻结期限/v0执行行为，不能改阈值或为随机性重跑门禁。",
  "stages": [
    {
      "stage": "Chap12",
      "status": "passed",
      "report": {
        "stage": "Chap12",
        "spec_version": "v0.3.1",
        "gate_scope": "system_gate",
        "system_gate_executed": true,
        "status": "passed",
        "checks": [
          {
            "check": "36_S07_cells",
            "expected": true,
            "observed": true,
            "status": "passed"
          },
          {
            "check": "AC12-01",
            "expected": true,
            "observed": true,
            "status": "passed"
          },
          {
            "check": "AC12-02",
            "expected": true,
            "observed": true,
            "status": "passed"
          },
          {
            "check": "AC12-10",
            "expected": true,
            "observed": true,
            "status": "passed"
          },
          {
            "check": "AC12-11",
            "expected": true,
            "observed": true,
            "status": "passed"
          },
          {
            "check": "AC12-13",
            "expected": true,
            "observed": true,
            "status": "passed"
          },
          {
            "check": "AC12-16",
            "expected": true,
            "observed": true,
            "status": "passed"
          },
          {
            "check": "AC12-23(a)",
            "expected": true,
            "observed": true,
            "status": "passed"
          },
          {
            "check": "budget_frozen",
            "expected": true,
            "observed": true,
            "status": "passed"
          },
          {
            "check": "component_checks",
            "expected": true,
            "observed": true,
            "status": "passed"
          },
          {
            "check": "frozen_v0_unchanged",
            "expected": true,
            "observed": true,
            "status": "passed"
          },
          {
            "check": "independent_count_recomputation",
            "expected": true,
            "observed": true,
            "status": "passed"
          },
          {
            "check": "old_multiagent_regression",
            "expected": true,
            "observed": true,
            "status": "passed"
          }
        ],
        "repair_rounds": 0,
        "chapter_repair_rounds": 1,
        "limits": {
          "attempts": 19,
          "llm_calls": 6,
          "seconds": 37.941018
        },
        "failure_items": [],
        "heldout_stage_calls_project2": 0,
        "engineering_gate_only": true,
        "comparison_and_heldout_pending": false,
        "evidence_files": [
          "audit\\project2-v1\\v031_ch12_components_round0.junit.xml",
          "audit/project2-v1/v031_ch12_extras_round0.json",
          "audit/project2-v1/v031_independent_counts.json"
        ],
        "stage_execution_completion_file": "audit/project2-v1/v031_ch12_completion.json",
        "stage_execution_completion_sha256": "e759ea50a034312d48cbeb7e8de6335259b844046601b52b6530239abfc54094",
        "answer_quality_acceptance": "not_accepted"
      },
      "quality": "S14未通过"
    },
    {
      "stage": "Chap13",
      "status": "failed",
      "report": {
        "stage": "Chap13",
        "status": "failed",
        "system_gate_executed": true,
        "gate_scope": "system_gate",
        "checks": [
          {
            "check": "budget_not_reset",
            "expected": true,
            "observed": true,
            "status": "passed",
            "evidence_type": "故障注入",
            "evidence_file": "audit/project2-v1/ch13_v032_round0/native_observations.json"
          },
          {
            "check": "completed_database_skipped",
            "expected": true,
            "observed": true,
            "status": "passed",
            "evidence_type": "真实运行",
            "evidence_file": "audit/project2-v1/ch13_v032_round0/native_observations.json"
          },
          {
            "check": "frozen_budget_and_baseline",
            "expected": true,
            "observed": true,
            "status": "passed",
            "evidence_type": "真实运行",
            "evidence_file": "audit/project2-v1/ch13_v032_round0/native_observations.json"
          },
          {
            "check": "heldout_reuse_only",
            "expected": true,
            "observed": true,
            "status": "passed",
            "evidence_type": "真实运行",
            "evidence_file": "audit/project2-v1/ch13_v032_round0/native_observations.json"
          },
          {
            "check": "illegal_state_rejected",
            "expected": true,
            "observed": true,
            "status": "passed",
            "evidence_type": "故障注入",
            "evidence_file": "audit/project2-v1/ch13_v032_round0/native_observations.json"
          },
          {
            "check": "owner_read_resume_isolation",
            "expected": true,
            "observed": true,
            "status": "passed",
            "evidence_type": "真实运行",
            "evidence_file": "audit/project2-v1/ch13_v032_round0/native_observations.json"
          },
          {
            "check": "parent_child_trace",
            "expected": true,
            "observed": true,
            "status": "passed",
            "evidence_type": "真实运行",
            "evidence_file": "audit/project2-v1/ch13_v032_round0/native_observations.json"
          },
          {
            "check": "read_only_policy_unregistered_publish",
            "expected": true,
            "observed": true,
            "status": "passed",
            "evidence_type": "真实运行",
            "evidence_file": "audit/project2-v1/ch13_v032_round0/native_observations.json"
          },
          {
            "check": "real_sqlite_fault_located_by_trace",
            "expected": true,
            "observed": true,
            "status": "passed",
            "evidence_type": "故障注入",
            "evidence_file": "audit/project2-v1/ch13_v032_round0/native_observations.json"
          },
          {
            "check": "real_subprocess_restart",
            "expected": true,
            "observed": true,
            "status": "passed",
            "evidence_type": "故障注入",
            "evidence_file": "audit/project2-v1/ch13_v032_round0/native_observations.json"
          },
          {
            "check": "revocation_rechecked",
            "expected": true,
            "observed": true,
            "status": "passed",
            "evidence_type": "真实运行",
            "evidence_file": "audit/project2-v1/ch13_v032_round0/native_observations.json"
          },
          {
            "check": "runtime_contract_tests",
            "expected": true,
            "observed": true,
            "status": "passed",
            "evidence_type": "契约测试(Mock)",
            "evidence_file": "audit/project2-v1/ch13_v032_round0/native_observations.json"
          },
          {
            "check": "same_run_id",
            "expected": true,
            "observed": false,
            "status": "failed",
            "evidence_type": "真实运行",
            "evidence_file": "audit/project2-v1/ch13_v032_round0/native_observations.json"
          },
          {
            "check": "unchanged_native_answer_body",
            "expected": true,
            "observed": false,
            "status": "failed",
            "evidence_type": "真实运行",
            "evidence_file": "audit/project2-v1/ch13_v032_round0/native_observations.json"
          },
          {
            "check": "unknown_run_rejected",
            "expected": true,
            "observed": true,
            "status": "passed",
            "evidence_type": "真实运行",
            "evidence_file": "audit/project2-v1/ch13_v032_round0/native_observations.json"
          }
        ],
        "failure_items": [
          "same_run_id",
          "unchanged_native_answer_body"
        ],
        "repair_rounds": 0,
        "plan_sha256": "9bdaa3fd90f70a92b0ab7a6d02b6b4f1a1dd8c6abba6e11e854a09ab07901b38",
        "native_error": null,
        "s14_status": "未通过",
        "heldout_new_calls": 0,
        "budget_limits_changed": false
      }
    },
    {
      "stage": "Chap14",
      "status": "not_executed",
      "report": null
    },
    {
      "stage": "Chap15",
      "status": "not_executed",
      "report": null
    }
  ],
  "branch": "codex/project2-ch13-v032",
  "traceability_counts": {
    "通过": 0,
    "部分": 36,
    "未完成": 25
  },
  "two_table_consistency": {
    "status": "passed",
    "approved_rows": 61,
    "runtime_rows": 61,
    "id_counts_match": true,
    "issues": [],
    "semantic_rule": "approved pending is design state; runtime execution state is separate; passed requires real complete gate evidence"
  },
  "native_stop": {
    "status": "stopped_frozen_active_execution",
    "machine_predicate": true,
    "permission_to_increase_budget": false,
    "stochastic_rerun_permitted": false,
    "gate_passed": false,
    "repairs_used": 0,
    "stage": "Chap13",
    "failed_checks": [
      "same_run_id",
      "unchanged_native_answer_body"
    ],
    "gate_passes": 13,
    "gate_total": 15,
    "limits": {
      "attempts": 19,
      "llm_calls": 6,
      "seconds": 37.941018
    },
    "usage": {
      "attempts": 15,
      "llm_calls": 4,
      "attempts_by_kind": {
        "db": 10,
        "llm": 4,
        "embedding": 1
      },
      "absolute_deadline": 1791335521.003568,
      "observed_tokens": null,
      "estimated_tokens": null,
      "cost": null,
      "execution": {
        "policy_sha256": "c76c2c52bdfb08cdccd12fb9b6aa32947d0e7e2493123d6b0321eb52d0b2582f",
        "limit_seconds": 37.941018,
        "lifetime_seconds": 900,
        "heartbeat_seconds": 0.25,
        "consumed_seconds": 38.46799999999348,
        "segments": [
          {
            "segment_id": "28f59612ef5b4035a16bcf2a79fc1086",
            "consumed_seconds": 2.14000000001397,
            "closed": true,
            "termination": "uncertain_tail_conservatively_charged"
          },
          {
            "segment_id": "ab9530be471343d1bff63a34307fa51e",
            "consumed_seconds": 36.32799999997951,
            "closed": false
          }
        ]
      }
    },
    "recovery_accounting": {
      "before": {
        "policy_sha256": "c76c2c52bdfb08cdccd12fb9b6aa32947d0e7e2493123d6b0321eb52d0b2582f",
        "limit_seconds": 37.941018,
        "lifetime_seconds": 900,
        "heartbeat_seconds": 0.25,
        "consumed_seconds": 1.8900000000139698,
        "segments": [
          {
            "segment_id": "28f59612ef5b4035a16bcf2a79fc1086",
            "consumed_seconds": 1.8900000000139698,
            "closed": false
          }
        ]
      },
      "after": {
        "policy_sha256": "c76c2c52bdfb08cdccd12fb9b6aa32947d0e7e2493123d6b0321eb52d0b2582f",
        "limit_seconds": 37.941018,
        "lifetime_seconds": 900,
        "heartbeat_seconds": 0.25,
        "consumed_seconds": 38.46799999999348,
        "segments": [
          {
            "segment_id": "28f59612ef5b4035a16bcf2a79fc1086",
            "consumed_seconds": 2.14000000001397,
            "closed": true,
            "termination": "uncertain_tail_conservatively_charged"
          },
          {
            "segment_id": "ab9530be471343d1bff63a34307fa51e",
            "consumed_seconds": 36.32799999997951,
            "closed": true,
            "termination": "normal_api_exit"
          }
        ]
      },
      "numeric_limits_unchanged": true,
      "attempts_preserved": true,
      "cumulative_not_reset": true,
      "expiry_rejections": true,
      "startup_evidence": [
        "after_restart_startup.json",
        "before_stop_startup.json",
        "expiry_checks_startup.json",
        "sqlite_fault_startup.json"
      ],
      "downtime_excluded": true,
      "evidence_type": "真实运行 / 故障注入"
    },
    "process_launch_seconds": 0.4159390926361084,
    "process_launch_to_ready_seconds": 24.92893648147583,
    "index_load_seconds": 4.86467579996679,
    "last_pending_dependency": {
      "kind": "llm",
      "attempts": 15,
      "llm_calls": 4
    },
    "host_guard": {
      "status": "released",
      "host_suspended": false,
      "gaps": [],
      "failure": null,
      "power_plugged": null,
      "psutil_installed": false,
      "calls": [
        {
          "flags": 2147483649,
          "previous": 2147483648
        },
        {
          "flags": 2147483648,
          "previous": 2147483649
        }
      ],
      "process_id": 112616,
      "system_power_settings_changed": false
    },
    "reason": "累计执行期限37.941018秒耗尽，恢复仍为RAG timeout/DB completed→partial；停机已排除。根因属于冻结期限/v0执行行为，不能改阈值或为随机性重跑门禁。",
    "proof_files": {
      "audit/project2-v1/ch13_v032_round0/gate.json": "2bae9d228dc54b8973f0d734a7145ff09219de7c12d0c5abd86ed1243f45c8d5",
      "audit/project2-v1/ch13_v032_round0/resumed_response.json": "85ec8a21cf2331f6abdfde861ee26a4f054c9e1cebbab569449339bcd6733347",
      "audit/project2-v1/ch13_v032_round0/recovery_accounting_evidence.json": "5271746c8050085f805f5b4169b6e483960f769a32acf1b95ac4f392ff76bbab",
      "audit/project2-v1/ch13_v032_round0/resume_trace.json": "a7d50b6d5d31c781eed0e140610b7bcac1416741aa7f28b9a0f2d33a7a2650fb",
      "audit/project2-v1/ch13_v032_round0/after_restart_startup.json": "2c48c182120310b30fc787693cac8616da753c1eb69346fe65fa7519a74f4ba6"
    }
  },
  "heldout_stage_calls_project2": 1,
  "heldout_repetitions_project2": 3,
  "chap13_heldout_new_calls": 0,
  "qa_engineering_gate_coverage": [
    {
      "name": "Chap12 QA修复前",
      "numerator": 45,
      "denominator": 117,
      "fraction": 0.38461538461538464,
      "metrics": {
        "mean": 0.38461538461538464,
        "range": [
          0.38461538461538464,
          0.38461538461538464
        ],
        "numerator": 45.0,
        "denominator": 117,
        "independent_query_groups": 39,
        "ci95": [
          0.24891373465561348,
          0.5410093854307493
        ],
        "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
        "per_repeat": [
          {
            "repeat": 1,
            "numerator": 15.0,
            "denominator": 39,
            "value": 0.38461538461538464,
            "ci95": [
              0.24891373465561348,
              0.5410093854307493
            ],
            "ci_method": "Wilson, independent query groups within repeat"
          },
          {
            "repeat": 2,
            "numerator": 15.0,
            "denominator": 39,
            "value": 0.38461538461538464,
            "ci95": [
              0.24891373465561348,
              0.5410093854307493
            ],
            "ci_method": "Wilson, independent query groups within repeat"
          },
          {
            "repeat": 3,
            "numerator": 15.0,
            "denominator": 39,
            "value": 0.38461538461538464,
            "ci95": [
              0.24891373465561348,
              0.5410093854307493
            ],
            "ci_method": "Wilson, independent query groups within repeat"
          }
        ],
        "interpretation": "estimate with CI",
        "repeated_runs_are_independent_questions": false
      }
    },
    {
      "name": "QA修复1（仅tune）",
      "numerator": 9,
      "denominator": 117,
      "fraction": 0.07692307692307693,
      "metrics": {
        "mean": 0.07692307692307693,
        "range": [
          0.05128205128205128,
          0.10256410256410256
        ],
        "numerator": 9.0,
        "denominator": 117,
        "independent_query_groups": 39,
        "ci95": [
          0.014177955415274113,
          0.23578854462856527
        ],
        "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
        "per_repeat": [
          {
            "repeat": 1,
            "numerator": 2.0,
            "denominator": 39,
            "value": 0.05128205128205128,
            "ci95": [
              0.014177955415274113,
              0.16885640047613612
            ],
            "ci_method": "Wilson, independent query groups within repeat"
          },
          {
            "repeat": 2,
            "numerator": 3.0,
            "denominator": 39,
            "value": 0.07692307692307693,
            "ci95": [
              0.02650739530377974,
              0.20321071167954996
            ],
            "ci_method": "Wilson, independent query groups within repeat"
          },
          {
            "repeat": 3,
            "numerator": 4.0,
            "denominator": 39,
            "value": 0.10256410256410256,
            "ci95": [
              0.04061331344668381,
              0.23578854462856527
            ],
            "ci_method": "Wilson, independent query groups within repeat"
          }
        ],
        "interpretation": "estimate with CI",
        "repeated_runs_are_independent_questions": false
      }
    }
  ],
  "post_v032_smoke": null,
  "state_distributions": {
    "Chap12组合": {
      "denominator": 150,
      "counts": {
        "completed": 129,
        "partial": 15,
        "no_data": 0,
        "permission_denied": 0,
        "timeout": 0,
        "failed": 6
      },
      "sum_verified": true,
      "source": "C:/Users/zacha/Documents/Ingestion Pipeline/evals/project2-v1/ch12/business.requests.jsonl",
      "source_sha256": "fd31bacb77b9174e793ead0e908b04a0fb3bb4587a97db48ae3ad28de2bfccee"
    },
    "Chap12 QA修复前": {
      "denominator": 117,
      "counts": {
        "completed": 52,
        "partial": 20,
        "no_data": 0,
        "permission_denied": 0,
        "timeout": 0,
        "failed": 45
      },
      "sum_verified": true,
      "source": "C:/Users/zacha/Documents/Ingestion Pipeline/evals/project2-v1/ch12/qa-tune/requests.jsonl",
      "source_sha256": "4e54c7d20290c71450c5ee26a90d40198fb1d13f03352522f6aa48d15fbe9902"
    },
    "QA修复1（仅tune）": {
      "denominator": 117,
      "counts": {
        "completed": 67,
        "partial": 41,
        "no_data": 0,
        "permission_denied": 0,
        "timeout": 3,
        "failed": 6
      },
      "sum_verified": true,
      "source": "C:/Users/zacha/Documents/Ingestion Pipeline/evals/project2-v1/ch12/regression_repair1/requests.jsonl",
      "source_sha256": "29e3116e20808cd0418624b720148f5bb04542a4c307c08485efe993a9505f7b"
    },
    "Chap12 held-out（历史）": {
      "denominator": 90,
      "counts": {
        "completed": 37,
        "partial": 14,
        "no_data": 0,
        "permission_denied": 0,
        "timeout": 0,
        "failed": 39
      },
      "sum_verified": true,
      "source": "C:/Users/zacha/Documents/Ingestion Pipeline/evals/project2-v1/ch12/qa-held-out/requests.jsonl",
      "source_sha256": "adc6587a485564345e60aa6bf7053d939f7d19328bb205755231b3204adccabf"
    },
    "N组合（历史）": {
      "denominator": 549,
      "counts": {
        "completed": 282,
        "partial": 75,
        "no_data": 0,
        "permission_denied": 0,
        "timeout": 0,
        "failed": 192
      },
      "sum_verified": true,
      "source": "C:/Users/zacha/Documents/Ingestion Pipeline/audit/project2-v1/v031_native_requests_round1.jsonl",
      "source_sha256": "e182333011404963a097b7a4058f2975b07bc4fa26f96b04a914c0385e4e51c6"
    },
    "Chap13恢复/故障请求": {
      "counts": {
        "completed": 0,
        "partial": 2,
        "no_data": 0,
        "permission_denied": 0,
        "timeout": 0,
        "failed": 0
      },
      "denominator": 2,
      "sum_verified": true
    }
  },
  "scoring_status": "待盲评",
  "old_scoring_status": "作废：空正文、全同分、基于修复前答案",
  "agreement_quoted": false,
  "idle_cleanup_evidence": {
    "passed": true,
    "process_returncode": 0,
    "pid": 110148,
    "ready_worker_pid": 90496,
    "cleanup": {
      "mode": "idle_eof",
      "elapsed_seconds": 1.7564402999123558,
      "process_retained": false
    },
    "evidence_type": "真实运行",
    "QA_requests": 0,
    "LLM_requests": 0,
    "old_records_rerun": false
  },
  "blind_export": {
    "status": "exported_historical_only",
    "current_v032_acceptance": false,
    "nonempty_answer_groups": 42,
    "nonempty_answer_observations": 192,
    "auto_zero_observations": 42,
    "all_observations": 234,
    "LLM_calls": 0,
    "scoring_status": "待盲评",
    "public_json": "evals/project2-v1/blind_review_20261006/public/blind_review.json",
    "public_markdown": "evals/project2-v1/blind_review_20261006/public/blind_review.md",
    "key_file": "evals/project2-v1/blind_review_20261006/private/key.json",
    "files": {
      "evals/project2-v1/blind_review_20261006/public/blind_review.json": "9f31be524f8a85746ced7616f3ce8108ae94825d04a1d717a4bee66833a721ea",
      "evals/project2-v1/blind_review_20261006/public/blind_review.md": "2798990d35f1884a9c92a8608c2985c509bd7d3c926faa9c1671a66971ba5603",
      "evals/project2-v1/blind_review_20261006/private/key.json": "fe0c7e13ee13a3723028d76e2365f0082c565247951c6b83b69b59f6be70ed96",
      "evals/project2-v1/blind_review_20261006/private/export_plan.json": "75604a95622c8381b8c357df1693b3a280c64c147aadf2760dab551391a4d5c8"
    }
  },
  "revision_history": [
    {
      "version": "v0.2",
      "delta_count": 2
    },
    {
      "version": "v0.3",
      "delta_count": 10
    },
    {
      "version": "v0.3.1",
      "delta_count": 1
    },
    {
      "version": "v0.3.2",
      "delta_count": 4
    }
  ],
  "document_check_lines": 14,
  "spec_manifest_sha256": "9c4addae69dc0f31b45e8461089eba84a718459d41d5a7051ed61e2096a9ac44",
  "baseline_sut_files_unchanged": 65,
  "s14_status": "未通过",
  "control_regression_old": {
    "questions": 7,
    "observations": 19
  },
  "remaining_regression_attribution": {
    "预算/超时导致的partial或timeout": 9
  },
  "qa_case_attribution": {
    "v0_RAG_refusal_with_real_DB_data": 5,
    "frozen_database_statement_limit": 6,
    "frozen_request_deadline_or_cold_restart": 33,
    "P2_slot_parser_missing_literal_component": 6
  },
  "repair1_metrics": {
    "recall_at_5": {
      "mean": 0.41666666666666663,
      "range": [
        0.3,
        0.6
      ],
      "numerator": 25.0,
      "denominator": 60,
      "independent_query_groups": 20,
      "ci95": [
        0.1454772448676043,
        0.781193467627183
      ],
      "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
      "per_repeat": [
        {
          "repeat": 1,
          "numerator": 12.0,
          "denominator": 20,
          "value": 0.6,
          "ci95": [
            0.3865815007622531,
            0.781193467627183
          ],
          "ci_method": "Wilson, independent query groups within repeat"
        },
        {
          "repeat": 2,
          "numerator": 7.0,
          "denominator": 20,
          "value": 0.35,
          "ci95": [
            0.18119182410108206,
            0.5671457233147638
          ],
          "ci_method": "Wilson, independent query groups within repeat"
        },
        {
          "repeat": 3,
          "numerator": 6.0,
          "denominator": 20,
          "value": 0.3,
          "ci95": [
            0.1454772448676043,
            0.5189728183535235
          ],
          "ci_method": "Wilson, independent query groups within repeat"
        }
      ],
      "interpretation": "estimate with CI",
      "repeated_runs_are_independent_questions": false
    },
    "recall_at_10": {
      "mean": 0.48333333333333334,
      "range": [
        0.35,
        0.65
      ],
      "numerator": 29.0,
      "denominator": 60,
      "independent_query_groups": 20,
      "ci95": [
        0.18119182410108206,
        0.818808175898918
      ],
      "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
      "per_repeat": [
        {
          "repeat": 1,
          "numerator": 13.0,
          "denominator": 20,
          "value": 0.65,
          "ci95": [
            0.43285427668523624,
            0.818808175898918
          ],
          "ci_method": "Wilson, independent query groups within repeat"
        },
        {
          "repeat": 2,
          "numerator": 9.0,
          "denominator": 20,
          "value": 0.45,
          "ci95": [
            0.2581978582556243,
            0.6579146575496577
          ],
          "ci_method": "Wilson, independent query groups within repeat"
        },
        {
          "repeat": 3,
          "numerator": 7.0,
          "denominator": 20,
          "value": 0.35,
          "ci95": [
            0.18119182410108206,
            0.5671457233147638
          ],
          "ci_method": "Wilson, independent query groups within repeat"
        }
      ],
      "interpretation": "estimate with CI",
      "repeated_runs_are_independent_questions": false
    },
    "mrr": {
      "mean": 0.41865079365079366,
      "range": [
        0.30833333333333335,
        0.5821428571428572
      ],
      "numerator": 25.11904761904762,
      "denominator": 60,
      "independent_query_groups": 20,
      "ci95": [
        0.2567460317460318,
        0.5797619047619047
      ],
      "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
      "per_repeat": [
        {
          "repeat": 1,
          "numerator": 11.642857142857142,
          "denominator": 20,
          "value": 0.5821428571428572
        },
        {
          "repeat": 2,
          "numerator": 7.309523809523809,
          "denominator": 20,
          "value": 0.36547619047619045
        },
        {
          "repeat": 3,
          "numerator": 6.166666666666667,
          "denominator": 20,
          "value": 0.30833333333333335
        }
      ],
      "interpretation": "estimate with CI",
      "repeated_runs_are_independent_questions": false
    },
    "complete": {
      "mean": 0.5666666666666667,
      "range": [
        0.43333333333333335,
        0.7666666666666667
      ],
      "numerator": 51.0,
      "denominator": 90,
      "independent_query_groups": 30,
      "ci95": [
        0.2737748557646652,
        0.8820761185551049
      ],
      "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
      "per_repeat": [
        {
          "repeat": 1,
          "numerator": 23.0,
          "denominator": 30,
          "value": 0.7666666666666667,
          "ci95": [
            0.5907167384187784,
            0.8820761185551049
          ],
          "ci_method": "Wilson, independent query groups within repeat"
        },
        {
          "repeat": 2,
          "numerator": 15.0,
          "denominator": 30,
          "value": 0.5,
          "ci95": [
            0.33154125640533766,
            0.6684587435946623
          ],
          "ci_method": "Wilson, independent query groups within repeat"
        },
        {
          "repeat": 3,
          "numerator": 13.0,
          "denominator": 30,
          "value": 0.43333333333333335,
          "ci95": [
            0.2737748557646652,
            0.6080269299918639
          ],
          "ci_method": "Wilson, independent query groups within repeat"
        }
      ],
      "interpretation": "estimate with CI",
      "repeated_runs_are_independent_questions": false
    },
    "partial": {
      "mean": 0.0,
      "range": [
        0.0,
        0.0
      ],
      "numerator": 0.0,
      "denominator": 90,
      "independent_query_groups": 30,
      "ci95": [
        0.0,
        0.11351339317396876
      ],
      "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
      "per_repeat": [
        {
          "repeat": 1,
          "numerator": 0.0,
          "denominator": 30,
          "value": 0.0,
          "ci95": [
            0.0,
            0.11351339317396876
          ],
          "ci_method": "Wilson, independent query groups within repeat"
        },
        {
          "repeat": 2,
          "numerator": 0.0,
          "denominator": 30,
          "value": 0.0,
          "ci95": [
            0.0,
            0.11351339317396876
          ],
          "ci_method": "Wilson, independent query groups within repeat"
        },
        {
          "repeat": 3,
          "numerator": 0.0,
          "denominator": 30,
          "value": 0.0,
          "ci95": [
            0.0,
            0.11351339317396876
          ],
          "ci_method": "Wilson, independent query groups within repeat"
        }
      ],
      "interpretation": "estimate with CI",
      "repeated_runs_are_independent_questions": false
    },
    "body_token_f1": {
      "mean": 0.23969291537928716,
      "range": [
        0.16034866500582512,
        0.3451649161046979
      ],
      "numerator": 14.38157492275723,
      "denominator": 60,
      "independent_query_groups": 20,
      "ci95": [
        0.13533144264850747,
        0.359302082809184
      ],
      "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
      "per_repeat": [
        {
          "repeat": 1,
          "numerator": 6.903298322093958,
          "denominator": 20,
          "value": 0.3451649161046979
        },
        {
          "repeat": 2,
          "numerator": 3.2069733001165024,
          "denominator": 20,
          "value": 0.16034866500582512
        },
        {
          "repeat": 3,
          "numerator": 4.271303300546768,
          "denominator": 20,
          "value": 0.21356516502733844
        }
      ],
      "interpretation": "estimate with CI",
      "repeated_runs_are_independent_questions": false
    },
    "n_refusal_proxy": {
      "mean": 0.0,
      "range": [
        0.0,
        0.0
      ],
      "numerator": 0.0,
      "denominator": 30,
      "independent_query_groups": 10,
      "ci95": [
        0.0,
        0.2775327998628892
      ],
      "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
      "per_repeat": [
        {
          "repeat": 1,
          "numerator": 0.0,
          "denominator": 10,
          "value": 0.0,
          "ci95": [
            0.0,
            0.2775327998628892
          ],
          "ci_method": "Wilson, independent query groups within repeat"
        },
        {
          "repeat": 2,
          "numerator": 0.0,
          "denominator": 10,
          "value": 0.0,
          "ci95": [
            0.0,
            0.2775327998628892
          ],
          "ci_method": "Wilson, independent query groups within repeat"
        },
        {
          "repeat": 3,
          "numerator": 0.0,
          "denominator": 10,
          "value": 0.0,
          "ci95": [
            0.0,
            0.2775327998628892
          ],
          "ci_method": "Wilson, independent query groups within repeat"
        }
      ],
      "interpretation": "estimate with CI",
      "repeated_runs_are_independent_questions": false
    }
  },
  "n_refusal_history": {
    "metric_is_gate": false,
    "numerator": 56,
    "denominator": 549,
    "wilson95_pooled_descriptive": [
      0.0793894410115606,
      0.13014885784866578
    ],
    "cluster_bootstrap95": [
      0.06060606060606061,
      0.14652014652014653
    ],
    "independent_query_clusters": 180,
    "mean": 0.10200364298724955,
    "range": [
      0.09836065573770492,
      0.1092896174863388
    ],
    "repeats": [
      {
        "repeat": 1,
        "refusals": 20,
        "total": 183,
        "wilson95": [
          0.07186990063645454,
          0.1627753386879044
        ],
        "states": {
          "failed": 64,
          "completed": 93,
          "no_data": 20,
          "timeout": 6
        }
      },
      {
        "repeat": 2,
        "refusals": 18,
        "total": 183,
        "wilson95": [
          0.06312617752041033,
          0.15011053702980479
        ],
        "states": {
          "failed": 64,
          "completed": 96,
          "no_data": 18,
          "timeout": 5
        }
      },
      {
        "repeat": 3,
        "refusals": 18,
        "total": 183,
        "wilson95": [
          0.06312617752041033,
          0.15011053702980479
        ],
        "states": {
          "failed": 64,
          "completed": 96,
          "no_data": 18,
          "timeout": 5
        }
      }
    ],
    "baseline_v0_conclusion_unchanged": true,
    "project2_claims_quality_improvement": false,
    "scope_limitation": "Official N label covers original candidate documents, not absence of any full-corpus answer; accepted cases require independent applicability review."
  },
  "same_partition_qa_comparison": [
    {
      "partition": "tune",
      "v0": {
        "body_f1_correct_citation": {
          "ci95": [
            0.21876702767614464,
            0.5413270932872238
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "denominator": 60,
          "independent_query_groups": 20,
          "interpretation": "estimate with CI",
          "mean": 0.3755709000657629,
          "numerator": 22.534254003945772,
          "per_repeat": [
            {
              "denominator": 20,
              "numerator": 7.511418001315257,
              "repeat": 1,
              "value": 0.3755709000657629
            },
            {
              "denominator": 20,
              "numerator": 7.511418001315257,
              "repeat": 2,
              "value": 0.3755709000657629
            },
            {
              "denominator": 20,
              "numerator": 7.511418001315257,
              "repeat": 3,
              "value": 0.3755709000657629
            }
          ],
          "range": [
            0.3755709000657629,
            0.3755709000657629
          ],
          "repeated_runs_are_independent_questions": false
        },
        "body_token_f1": {
          "ci95": [
            0.26809100285503074,
            0.5623751126180483
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "denominator": 60,
          "independent_query_groups": 20,
          "interpretation": "estimate with CI",
          "mean": 0.4130411508435564,
          "numerator": 24.782469050613386,
          "per_repeat": [
            {
              "denominator": 20,
              "numerator": 8.291126047174158,
              "repeat": 1,
              "value": 0.41455630235870794
            },
            {
              "denominator": 20,
              "numerator": 8.291126047174158,
              "repeat": 2,
              "value": 0.41455630235870794
            },
            {
              "denominator": 20,
              "numerator": 8.200216956265068,
              "repeat": 3,
              "value": 0.41001084781325337
            }
          ],
          "range": [
            0.41001084781325337,
            0.41455630235870794
          ],
          "repeated_runs_are_independent_questions": false
        },
        "context_precision_at_5": {
          "ci95": [
            0.09000000000000001,
            0.17
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "denominator": 60,
          "independent_query_groups": 20,
          "interpretation": "estimate with CI",
          "mean": 0.13,
          "numerator": 7.800000000000001,
          "per_repeat": [
            {
              "denominator": 20,
              "numerator": 2.6,
              "repeat": 1,
              "value": 0.13
            },
            {
              "denominator": 20,
              "numerator": 2.6,
              "repeat": 2,
              "value": 0.13
            },
            {
              "denominator": 20,
              "numerator": 2.6,
              "repeat": 3,
              "value": 0.13
            }
          ],
          "range": [
            0.13,
            0.13
          ],
          "repeated_runs_are_independent_questions": false
        },
        "correct_document_cited": {
          "ci95": [
            0.43285427668523624,
            0.818808175898918
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "denominator": 60,
          "independent_query_groups": 20,
          "interpretation": "estimate with CI",
          "mean": 0.65,
          "numerator": 39.0,
          "per_repeat": [
            {
              "ci95": [
                0.43285427668523624,
                0.818808175898918
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 13.0,
              "repeat": 1,
              "value": 0.65
            },
            {
              "ci95": [
                0.43285427668523624,
                0.818808175898918
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 13.0,
              "repeat": 2,
              "value": 0.65
            },
            {
              "ci95": [
                0.43285427668523624,
                0.818808175898918
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 13.0,
              "repeat": 3,
              "value": 0.65
            }
          ],
          "range": [
            0.65,
            0.65
          ],
          "repeated_runs_are_independent_questions": false
        },
        "error_rate": {
          "ci95": [
            0.0,
            0.11351339317396876
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "denominator": 90,
          "independent_query_groups": 30,
          "interpretation": "estimate with CI",
          "mean": 0.0,
          "numerator": 0.0,
          "per_repeat": [
            {
              "ci95": [
                0.0,
                0.11351339317396876
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 30,
              "numerator": 0.0,
              "repeat": 1,
              "value": 0.0
            },
            {
              "ci95": [
                0.0,
                0.11351339317396876
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 30,
              "numerator": 0.0,
              "repeat": 2,
              "value": 0.0
            },
            {
              "ci95": [
                0.0,
                0.11351339317396876
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 30,
              "numerator": 0.0,
              "repeat": 3,
              "value": 0.0
            }
          ],
          "range": [
            0.0,
            0.0
          ],
          "repeated_runs_are_independent_questions": false
        },
        "latency_ms": {
          "ci95": [
            11363.928296662763,
            14092.041011114554
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "denominator": 90,
          "independent_query_groups": 30,
          "interpretation": "estimate with CI",
          "mean": 12693.355721112393,
          "numerator": 1142402.0149001153,
          "per_repeat": [
            {
              "denominator": 30,
              "numerator": 462844.25620012917,
              "repeat": 1,
              "value": 15428.14187333764
            },
            {
              "denominator": 30,
              "numerator": 336855.070900172,
              "repeat": 2,
              "value": 11228.502363339067
            },
            {
              "denominator": 30,
              "numerator": 342702.68779981416,
              "repeat": 3,
              "value": 11423.422926660473
            }
          ],
          "range": [
            11228.502363339067,
            15428.14187333764
          ],
          "repeated_runs_are_independent_questions": false
        },
        "llm_calls": {
          "ci95": [
            2.8555555555555556,
            3.0444444444444443
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "denominator": 90,
          "independent_query_groups": 30,
          "interpretation": "estimate with CI",
          "mean": 2.9555555555555553,
          "numerator": 266.0,
          "per_repeat": [
            {
              "denominator": 30,
              "numerator": 88.0,
              "repeat": 1,
              "value": 2.933333333333333
            },
            {
              "denominator": 30,
              "numerator": 88.0,
              "repeat": 2,
              "value": 2.933333333333333
            },
            {
              "denominator": 30,
              "numerator": 90.0,
              "repeat": 3,
              "value": 3.0
            }
          ],
          "range": [
            2.933333333333333,
            3.0
          ],
          "repeated_runs_are_independent_questions": false
        },
        "llm_tokens": {
          "ci95": [
            4526.377777777778,
            5206.777777777777
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "denominator": 90,
          "independent_query_groups": 30,
          "interpretation": "estimate with CI",
          "mean": 4862.666666666667,
          "numerator": 437640.0,
          "per_repeat": [
            {
              "denominator": 30,
              "numerator": 144178.0,
              "repeat": 1,
              "value": 4805.933333333333
            },
            {
              "denominator": 30,
              "numerator": 144169.0,
              "repeat": 2,
              "value": 4805.633333333333
            },
            {
              "denominator": 30,
              "numerator": 149293.0,
              "repeat": 3,
              "value": 4976.433333333333
            }
          ],
          "range": [
            4805.633333333333,
            4976.433333333333
          ],
          "repeated_runs_are_independent_questions": false
        },
        "mrr": {
          "ci95": [
            0.44880952380952377,
            0.8321428571428572
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "denominator": 60,
          "independent_query_groups": 20,
          "interpretation": "estimate with CI",
          "mean": 0.6488095238095238,
          "numerator": 38.92857142857143,
          "per_repeat": [
            {
              "denominator": 20,
              "numerator": 12.976190476190476,
              "repeat": 1,
              "value": 0.6488095238095238
            },
            {
              "denominator": 20,
              "numerator": 12.976190476190476,
              "repeat": 2,
              "value": 0.6488095238095238
            },
            {
              "denominator": 20,
              "numerator": 12.976190476190476,
              "repeat": 3,
              "value": 0.6488095238095238
            }
          ],
          "range": [
            0.6488095238095238,
            0.6488095238095238
          ],
          "repeated_runs_are_independent_questions": false
        },
        "n_refusal_proxy": {
          "ci95": [
            0.0,
            0.2775327998628892
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "denominator": 30,
          "independent_query_groups": 10,
          "interpretation": "estimate with CI",
          "mean": 0.0,
          "numerator": 0.0,
          "per_repeat": [
            {
              "ci95": [
                0.0,
                0.2775327998628892
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 10,
              "numerator": 0.0,
              "repeat": 1,
              "value": 0.0
            },
            {
              "ci95": [
                0.0,
                0.2775327998628892
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 10,
              "numerator": 0.0,
              "repeat": 2,
              "value": 0.0
            },
            {
              "ci95": [
                0.0,
                0.2775327998628892
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 10,
              "numerator": 0.0,
              "repeat": 3,
              "value": 0.0
            }
          ],
          "range": [
            0.0,
            0.0
          ],
          "repeated_runs_are_independent_questions": false
        },
        "recall_at_10": {
          "ci95": [
            0.5839825677481064,
            0.919342337420202
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "denominator": 60,
          "independent_query_groups": 20,
          "interpretation": "estimate with CI",
          "mean": 0.8,
          "numerator": 48.0,
          "per_repeat": [
            {
              "ci95": [
                0.5839825677481064,
                0.919342337420202
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 16.0,
              "repeat": 1,
              "value": 0.8
            },
            {
              "ci95": [
                0.5839825677481064,
                0.919342337420202
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 16.0,
              "repeat": 2,
              "value": 0.8
            },
            {
              "ci95": [
                0.5839825677481064,
                0.919342337420202
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 16.0,
              "repeat": 3,
              "value": 0.8
            }
          ],
          "range": [
            0.8,
            0.8
          ],
          "repeated_runs_are_independent_questions": false
        },
        "recall_at_5": {
          "ci95": [
            0.43285427668523624,
            0.818808175898918
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "denominator": 60,
          "independent_query_groups": 20,
          "interpretation": "estimate with CI",
          "mean": 0.65,
          "numerator": 39.0,
          "per_repeat": [
            {
              "ci95": [
                0.43285427668523624,
                0.818808175898918
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 13.0,
              "repeat": 1,
              "value": 0.65
            },
            {
              "ci95": [
                0.43285427668523624,
                0.818808175898918
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 13.0,
              "repeat": 2,
              "value": 0.65
            },
            {
              "ci95": [
                0.43285427668523624,
                0.818808175898918
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 13.0,
              "repeat": 3,
              "value": 0.65
            }
          ],
          "range": [
            0.65,
            0.65
          ],
          "repeated_runs_are_independent_questions": false
        },
        "reranker_fallback_rate": {
          "ci95": [
            0.0,
            0.11351339317396876
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "denominator": 90,
          "independent_query_groups": 30,
          "interpretation": "estimate with CI",
          "mean": 0.0,
          "numerator": 0.0,
          "per_repeat": [
            {
              "ci95": [
                0.0,
                0.11351339317396876
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 30,
              "numerator": 0.0,
              "repeat": 1,
              "value": 0.0
            },
            {
              "ci95": [
                0.0,
                0.11351339317396876
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 30,
              "numerator": 0.0,
              "repeat": 2,
              "value": 0.0
            },
            {
              "ci95": [
                0.0,
                0.11351339317396876
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 30,
              "numerator": 0.0,
              "repeat": 3,
              "value": 0.0
            }
          ],
          "range": [
            0.0,
            0.0
          ],
          "repeated_runs_are_independent_questions": false
        },
        "y_answered": {
          "ci95": [
            0.6395811352592431,
            0.9721335187862319
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "denominator": 60,
          "independent_query_groups": 20,
          "interpretation": "estimate with CI",
          "mean": 0.8833333333333333,
          "numerator": 53.0,
          "per_repeat": [
            {
              "ci95": [
                0.6989663547715128,
                0.9721335187862319
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 18.0,
              "repeat": 1,
              "value": 0.9
            },
            {
              "ci95": [
                0.6989663547715128,
                0.9721335187862319
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 18.0,
              "repeat": 2,
              "value": 0.9
            },
            {
              "ci95": [
                0.6395811352592431,
                0.9476312541037835
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 17.0,
              "repeat": 3,
              "value": 0.85
            }
          ],
          "range": [
            0.85,
            0.9
          ],
          "repeated_runs_are_independent_questions": false
        }
      },
      "chap12": {
        "recall_at_5": {
          "mean": 0.35,
          "range": [
            0.3,
            0.4
          ],
          "numerator": 21.0,
          "denominator": 60,
          "independent_query_groups": 20,
          "ci95": [
            0.1454772448676043,
            0.6134184992377469
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 7.0,
              "denominator": 20,
              "value": 0.35,
              "ci95": [
                0.18119182410108206,
                0.5671457233147638
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 2,
              "numerator": 6.0,
              "denominator": 20,
              "value": 0.3,
              "ci95": [
                0.1454772448676043,
                0.5189728183535235
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 3,
              "numerator": 8.0,
              "denominator": 20,
              "value": 0.4,
              "ci95": [
                0.21880653237281705,
                0.6134184992377469
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "recall_at_10": {
          "mean": 0.4,
          "range": [
            0.35,
            0.45
          ],
          "numerator": 24.0,
          "denominator": 60,
          "independent_query_groups": 20,
          "ci95": [
            0.18119182410108206,
            0.6579146575496577
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 8.0,
              "denominator": 20,
              "value": 0.4,
              "ci95": [
                0.21880653237281705,
                0.6134184992377469
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 2,
              "numerator": 7.0,
              "denominator": 20,
              "value": 0.35,
              "ci95": [
                0.18119182410108206,
                0.5671457233147638
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 3,
              "numerator": 9.0,
              "denominator": 20,
              "value": 0.45,
              "ci95": [
                0.2581978582556243,
                0.6579146575496577
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "mrr": {
          "mean": 0.33214285714285713,
          "range": [
            0.28214285714285714,
            0.3821428571428571
          ],
          "numerator": 19.928571428571427,
          "denominator": 60,
          "independent_query_groups": 20,
          "ci95": [
            0.16547619047619047,
            0.5
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 6.642857142857143,
              "denominator": 20,
              "value": 0.33214285714285713
            },
            {
              "repeat": 2,
              "numerator": 5.642857142857143,
              "denominator": 20,
              "value": 0.28214285714285714
            },
            {
              "repeat": 3,
              "numerator": 7.642857142857143,
              "denominator": 20,
              "value": 0.3821428571428571
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "correct_document_cited": {
          "mean": 0.31666666666666665,
          "range": [
            0.3,
            0.35
          ],
          "numerator": 19.0,
          "denominator": 60,
          "independent_query_groups": 20,
          "ci95": [
            0.1454772448676043,
            0.5671457233147638
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 6.0,
              "denominator": 20,
              "value": 0.3,
              "ci95": [
                0.1454772448676043,
                0.5189728183535235
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 2,
              "numerator": 6.0,
              "denominator": 20,
              "value": 0.3,
              "ci95": [
                0.1454772448676043,
                0.5189728183535235
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 3,
              "numerator": 7.0,
              "denominator": 20,
              "value": 0.35,
              "ci95": [
                0.18119182410108206,
                0.5671457233147638
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "n_refusal_proxy": {
          "mean": 0.0,
          "range": [
            0.0,
            0.0
          ],
          "numerator": 0.0,
          "denominator": 30,
          "independent_query_groups": 10,
          "ci95": [
            0.0,
            0.2775327998628892
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 0.0,
              "denominator": 10,
              "value": 0.0,
              "ci95": [
                0.0,
                0.2775327998628892
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 2,
              "numerator": 0.0,
              "denominator": 10,
              "value": 0.0,
              "ci95": [
                0.0,
                0.2775327998628892
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 3,
              "numerator": 0.0,
              "denominator": 10,
              "value": 0.0,
              "ci95": [
                0.0,
                0.2775327998628892
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "complete": {
          "mean": 0.45555555555555555,
          "range": [
            0.4,
            0.5
          ],
          "numerator": 41.0,
          "denominator": 90,
          "independent_query_groups": 30,
          "ci95": [
            0.24590628116801852,
            0.6684587435946623
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 12.0,
              "denominator": 30,
              "value": 0.4,
              "ci95": [
                0.24590628116801852,
                0.5767963974667752
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 2,
              "numerator": 15.0,
              "denominator": 30,
              "value": 0.5,
              "ci95": [
                0.33154125640533766,
                0.6684587435946623
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 3,
              "numerator": 14.0,
              "denominator": 30,
              "value": 0.4666666666666667,
              "ci95": [
                0.30232388907699753,
                0.638577003801267
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "partial": {
          "mean": 0.0,
          "range": [
            0.0,
            0.0
          ],
          "numerator": 0.0,
          "denominator": 90,
          "independent_query_groups": 30,
          "ci95": [
            0.0,
            0.11351339317396876
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 0.0,
              "denominator": 30,
              "value": 0.0,
              "ci95": [
                0.0,
                0.11351339317396876
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 2,
              "numerator": 0.0,
              "denominator": 30,
              "value": 0.0,
              "ci95": [
                0.0,
                0.11351339317396876
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 3,
              "numerator": 0.0,
              "denominator": 30,
              "value": 0.0,
              "ci95": [
                0.0,
                0.11351339317396876
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "body_token_f1": {
          "mean": 0.20392365745195526,
          "range": [
            0.19309158638379592,
            0.2245403496346793
          ],
          "numerator": 12.235419447117314,
          "denominator": 60,
          "independent_query_groups": 20,
          "ci95": [
            0.09443892116300019,
            0.3344037544494549
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 3.861831727675918,
              "denominator": 20,
              "value": 0.19309158638379592
            },
            {
              "repeat": 2,
              "numerator": 3.8827807267478103,
              "denominator": 20,
              "value": 0.19413903633739052
            },
            {
              "repeat": 3,
              "numerator": 4.490806992693586,
              "denominator": 20,
              "value": 0.2245403496346793
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "elapsed_seconds": {
          "mean": 14.54905207333569,
          "range": [
            13.644424663344399,
            15.684348243339143
          ],
          "numerator": 1309.414686600212,
          "denominator": 90,
          "independent_query_groups": 30,
          "ci95": [
            10.277094686675506,
            19.02197062889528
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 470.5304473001743,
              "denominator": 30,
              "value": 15.684348243339143
            },
            {
              "repeat": 2,
              "numerator": 409.33273990033194,
              "denominator": 30,
              "value": 13.644424663344399
            },
            {
              "repeat": 3,
              "numerator": 429.5514993997058,
              "denominator": 30,
              "value": 14.318383313323526
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "attempts": {
          "mean": 8.177777777777777,
          "range": [
            7.8,
            8.433333333333334
          ],
          "numerator": 736.0,
          "denominator": 90,
          "independent_query_groups": 30,
          "ci95": [
            5.933333333333334,
            10.333333333333334
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 253.0,
              "denominator": 30,
              "value": 8.433333333333334
            },
            {
              "repeat": 2,
              "numerator": 249.0,
              "denominator": 30,
              "value": 8.3
            },
            {
              "repeat": 3,
              "numerator": 234.0,
              "denominator": 30,
              "value": 7.8
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "llm_calls": {
          "mean": 1.6333333333333333,
          "range": [
            1.5666666666666667,
            1.7
          ],
          "numerator": 147.0,
          "denominator": 90,
          "independent_query_groups": 30,
          "ci95": [
            1.1666666666666667,
            2.088888888888889
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 47.0,
              "denominator": 30,
              "value": 1.5666666666666667
            },
            {
              "repeat": 2,
              "numerator": 51.0,
              "denominator": 30,
              "value": 1.7
            },
            {
              "repeat": 3,
              "numerator": 49.0,
              "denominator": 30,
              "value": 1.6333333333333333
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        }
      }
    },
    {
      "partition": "held-out",
      "v0": {
        "body_f1_correct_citation": {
          "ci95": [
            0.08027643292233487,
            0.2725739571426677
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "denominator": 60,
          "independent_query_groups": 20,
          "interpretation": "estimate with CI",
          "mean": 0.17092572856080704,
          "numerator": 10.255543713648422,
          "per_repeat": [
            {
              "denominator": 20,
              "numerator": 3.4185145712161407,
              "repeat": 1,
              "value": 0.17092572856080704
            },
            {
              "denominator": 20,
              "numerator": 3.4185145712161407,
              "repeat": 2,
              "value": 0.17092572856080704
            },
            {
              "denominator": 20,
              "numerator": 3.4185145712161407,
              "repeat": 3,
              "value": 0.17092572856080704
            }
          ],
          "range": [
            0.17092572856080704,
            0.17092572856080704
          ],
          "repeated_runs_are_independent_questions": false
        },
        "body_token_f1": {
          "ci95": [
            0.20121000437928185,
            0.34347826693150024
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "denominator": 60,
          "independent_query_groups": 20,
          "interpretation": "estimate with CI",
          "mean": 0.2672664518151954,
          "numerator": 16.035987108911723,
          "per_repeat": [
            {
              "denominator": 20,
              "numerator": 5.345329036303908,
              "repeat": 1,
              "value": 0.2672664518151954
            },
            {
              "denominator": 20,
              "numerator": 5.345329036303908,
              "repeat": 2,
              "value": 0.2672664518151954
            },
            {
              "denominator": 20,
              "numerator": 5.345329036303908,
              "repeat": 3,
              "value": 0.2672664518151954
            }
          ],
          "range": [
            0.2672664518151954,
            0.2672664518151954
          ],
          "repeated_runs_are_independent_questions": false
        },
        "context_precision_at_5": {
          "ci95": [
            0.09000000000000001,
            0.17
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "denominator": 60,
          "independent_query_groups": 20,
          "interpretation": "estimate with CI",
          "mean": 0.13,
          "numerator": 7.800000000000001,
          "per_repeat": [
            {
              "denominator": 20,
              "numerator": 2.6,
              "repeat": 1,
              "value": 0.13
            },
            {
              "denominator": 20,
              "numerator": 2.6,
              "repeat": 2,
              "value": 0.13
            },
            {
              "denominator": 20,
              "numerator": 2.6,
              "repeat": 3,
              "value": 0.13
            }
          ],
          "range": [
            0.13,
            0.13
          ],
          "repeated_runs_are_independent_questions": false
        },
        "correct_document_cited": {
          "ci95": [
            0.2581978582556243,
            0.6579146575496577
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "denominator": 60,
          "independent_query_groups": 20,
          "interpretation": "estimate with CI",
          "mean": 0.45,
          "numerator": 27.0,
          "per_repeat": [
            {
              "ci95": [
                0.2581978582556243,
                0.6579146575496577
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 9.0,
              "repeat": 1,
              "value": 0.45
            },
            {
              "ci95": [
                0.2581978582556243,
                0.6579146575496577
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 9.0,
              "repeat": 2,
              "value": 0.45
            },
            {
              "ci95": [
                0.2581978582556243,
                0.6579146575496577
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 9.0,
              "repeat": 3,
              "value": 0.45
            }
          ],
          "range": [
            0.45,
            0.45
          ],
          "repeated_runs_are_independent_questions": false
        },
        "error_rate": {
          "ci95": [
            0.0,
            0.11351339317396876
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "denominator": 90,
          "independent_query_groups": 30,
          "interpretation": "estimate with CI",
          "mean": 0.0,
          "numerator": 0.0,
          "per_repeat": [
            {
              "ci95": [
                0.0,
                0.11351339317396876
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 30,
              "numerator": 0.0,
              "repeat": 1,
              "value": 0.0
            },
            {
              "ci95": [
                0.0,
                0.11351339317396876
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 30,
              "numerator": 0.0,
              "repeat": 2,
              "value": 0.0
            },
            {
              "ci95": [
                0.0,
                0.11351339317396876
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 30,
              "numerator": 0.0,
              "repeat": 3,
              "value": 0.0
            }
          ],
          "range": [
            0.0,
            0.0
          ],
          "repeated_runs_are_independent_questions": false
        },
        "latency_ms": {
          "ci95": [
            11826.561562218962,
            27668.948251108588
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "denominator": 90,
          "independent_query_groups": 30,
          "interpretation": "estimate with CI",
          "mean": 17325.893437775732,
          "numerator": 1559330.4093998158,
          "per_repeat": [
            {
              "denominator": 30,
              "numerator": 913117.0834002551,
              "repeat": 1,
              "value": 30437.236113341834
            },
            {
              "denominator": 30,
              "numerator": 328362.09909943864,
              "repeat": 2,
              "value": 10945.40330331462
            },
            {
              "denominator": 30,
              "numerator": 317851.2269001221,
              "repeat": 3,
              "value": 10595.040896670738
            }
          ],
          "range": [
            10595.040896670738,
            30437.236113341834
          ],
          "repeated_runs_are_independent_questions": false
        },
        "llm_calls": {
          "ci95": [
            2.9,
            3.0
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "denominator": 90,
          "independent_query_groups": 30,
          "interpretation": "estimate with CI",
          "mean": 2.966666666666667,
          "numerator": 267.0,
          "per_repeat": [
            {
              "denominator": 30,
              "numerator": 89.0,
              "repeat": 1,
              "value": 2.966666666666667
            },
            {
              "denominator": 30,
              "numerator": 89.0,
              "repeat": 2,
              "value": 2.966666666666667
            },
            {
              "denominator": 30,
              "numerator": 89.0,
              "repeat": 3,
              "value": 2.966666666666667
            }
          ],
          "range": [
            2.966666666666667,
            2.966666666666667
          ],
          "repeated_runs_are_independent_questions": false
        },
        "llm_tokens": {
          "ci95": [
            4432.133333333333,
            4876.222222222223
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "denominator": 90,
          "independent_query_groups": 30,
          "interpretation": "estimate with CI",
          "mean": 4649.4,
          "numerator": 418446.0,
          "per_repeat": [
            {
              "denominator": 30,
              "numerator": 139491.0,
              "repeat": 1,
              "value": 4649.7
            },
            {
              "denominator": 30,
              "numerator": 139491.0,
              "repeat": 2,
              "value": 4649.7
            },
            {
              "denominator": 30,
              "numerator": 139464.0,
              "repeat": 3,
              "value": 4648.8
            }
          ],
          "range": [
            4648.8,
            4649.7
          ],
          "repeated_runs_are_independent_questions": false
        },
        "mrr": {
          "ci95": [
            0.375,
            0.7866666666666667
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "denominator": 60,
          "independent_query_groups": 20,
          "interpretation": "estimate with CI",
          "mean": 0.5891666666666666,
          "numerator": 35.35,
          "per_repeat": [
            {
              "denominator": 20,
              "numerator": 11.783333333333333,
              "repeat": 1,
              "value": 0.5891666666666666
            },
            {
              "denominator": 20,
              "numerator": 11.783333333333333,
              "repeat": 2,
              "value": 0.5891666666666666
            },
            {
              "denominator": 20,
              "numerator": 11.783333333333333,
              "repeat": 3,
              "value": 0.5891666666666666
            }
          ],
          "range": [
            0.5891666666666666,
            0.5891666666666666
          ],
          "repeated_runs_are_independent_questions": false
        },
        "n_refusal_proxy": {
          "ci95": [
            0.017876213095072896,
            0.4041500267952385
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "denominator": 30,
          "independent_query_groups": 10,
          "interpretation": "estimate with CI",
          "mean": 0.1,
          "numerator": 3.0,
          "per_repeat": [
            {
              "ci95": [
                0.017876213095072896,
                0.4041500267952385
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 10,
              "numerator": 1.0,
              "repeat": 1,
              "value": 0.1
            },
            {
              "ci95": [
                0.017876213095072896,
                0.4041500267952385
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 10,
              "numerator": 1.0,
              "repeat": 2,
              "value": 0.1
            },
            {
              "ci95": [
                0.017876213095072896,
                0.4041500267952385
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 10,
              "numerator": 1.0,
              "repeat": 3,
              "value": 0.1
            }
          ],
          "range": [
            0.1,
            0.1
          ],
          "repeated_runs_are_independent_questions": false
        },
        "recall_at_10": {
          "ci95": [
            0.43285427668523624,
            0.818808175898918
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "denominator": 60,
          "independent_query_groups": 20,
          "interpretation": "estimate with CI",
          "mean": 0.65,
          "numerator": 39.0,
          "per_repeat": [
            {
              "ci95": [
                0.43285427668523624,
                0.818808175898918
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 13.0,
              "repeat": 1,
              "value": 0.65
            },
            {
              "ci95": [
                0.43285427668523624,
                0.818808175898918
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 13.0,
              "repeat": 2,
              "value": 0.65
            },
            {
              "ci95": [
                0.43285427668523624,
                0.818808175898918
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 13.0,
              "repeat": 3,
              "value": 0.65
            }
          ],
          "range": [
            0.65,
            0.65
          ],
          "repeated_runs_are_independent_questions": false
        },
        "recall_at_5": {
          "ci95": [
            0.43285427668523624,
            0.818808175898918
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "denominator": 60,
          "independent_query_groups": 20,
          "interpretation": "estimate with CI",
          "mean": 0.65,
          "numerator": 39.0,
          "per_repeat": [
            {
              "ci95": [
                0.43285427668523624,
                0.818808175898918
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 13.0,
              "repeat": 1,
              "value": 0.65
            },
            {
              "ci95": [
                0.43285427668523624,
                0.818808175898918
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 13.0,
              "repeat": 2,
              "value": 0.65
            },
            {
              "ci95": [
                0.43285427668523624,
                0.818808175898918
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 13.0,
              "repeat": 3,
              "value": 0.65
            }
          ],
          "range": [
            0.65,
            0.65
          ],
          "repeated_runs_are_independent_questions": false
        },
        "reranker_fallback_rate": {
          "ci95": [
            0.0,
            0.11351339317396876
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "denominator": 90,
          "independent_query_groups": 30,
          "interpretation": "estimate with CI",
          "mean": 0.0,
          "numerator": 0.0,
          "per_repeat": [
            {
              "ci95": [
                0.0,
                0.11351339317396876
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 30,
              "numerator": 0.0,
              "repeat": 1,
              "value": 0.0
            },
            {
              "ci95": [
                0.0,
                0.11351339317396876
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 30,
              "numerator": 0.0,
              "repeat": 2,
              "value": 0.0
            },
            {
              "ci95": [
                0.0,
                0.11351339317396876
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 30,
              "numerator": 0.0,
              "repeat": 3,
              "value": 0.0
            }
          ],
          "range": [
            0.0,
            0.0
          ],
          "repeated_runs_are_independent_questions": false
        },
        "y_answered": {
          "ci95": [
            0.763868806553258,
            0.9911185511992047
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "denominator": 60,
          "independent_query_groups": 20,
          "interpretation": "estimate with CI",
          "mean": 0.95,
          "numerator": 57.0,
          "per_repeat": [
            {
              "ci95": [
                0.763868806553258,
                0.9911185511992047
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 19.0,
              "repeat": 1,
              "value": 0.95
            },
            {
              "ci95": [
                0.763868806553258,
                0.9911185511992047
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 19.0,
              "repeat": 2,
              "value": 0.95
            },
            {
              "ci95": [
                0.763868806553258,
                0.9911185511992047
              ],
              "ci_method": "Wilson, independent query groups within repeat",
              "denominator": 20,
              "numerator": 19.0,
              "repeat": 3,
              "value": 0.95
            }
          ],
          "range": [
            0.95,
            0.95
          ],
          "repeated_runs_are_independent_questions": false
        }
      },
      "chap12": {
        "recall_at_5": {
          "mean": 0.31666666666666665,
          "range": [
            0.15,
            0.4
          ],
          "numerator": 19.0,
          "denominator": 60,
          "independent_query_groups": 20,
          "ci95": [
            0.052368745896216595,
            0.6134184992377469
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 8.0,
              "denominator": 20,
              "value": 0.4,
              "ci95": [
                0.21880653237281705,
                0.6134184992377469
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 2,
              "numerator": 3.0,
              "denominator": 20,
              "value": 0.15,
              "ci95": [
                0.052368745896216595,
                0.36041886474075696
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 3,
              "numerator": 8.0,
              "denominator": 20,
              "value": 0.4,
              "ci95": [
                0.21880653237281705,
                0.6134184992377469
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "recall_at_10": {
          "mean": 0.31666666666666665,
          "range": [
            0.15,
            0.4
          ],
          "numerator": 19.0,
          "denominator": 60,
          "independent_query_groups": 20,
          "ci95": [
            0.052368745896216595,
            0.6134184992377469
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 8.0,
              "denominator": 20,
              "value": 0.4,
              "ci95": [
                0.21880653237281705,
                0.6134184992377469
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 2,
              "numerator": 3.0,
              "denominator": 20,
              "value": 0.15,
              "ci95": [
                0.052368745896216595,
                0.36041886474075696
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 3,
              "numerator": 8.0,
              "denominator": 20,
              "value": 0.4,
              "ci95": [
                0.21880653237281705,
                0.6134184992377469
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "mrr": {
          "mean": 0.29944444444444446,
          "range": [
            0.15333333333333332,
            0.3725
          ],
          "numerator": 17.966666666666665,
          "denominator": 60,
          "independent_query_groups": 20,
          "ci95": [
            0.1377777777777778,
            0.4716666666666667
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 7.45,
              "denominator": 20,
              "value": 0.3725
            },
            {
              "repeat": 2,
              "numerator": 3.066666666666667,
              "denominator": 20,
              "value": 0.15333333333333332
            },
            {
              "repeat": 3,
              "numerator": 7.45,
              "denominator": 20,
              "value": 0.3725
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "correct_document_cited": {
          "mean": 0.23333333333333334,
          "range": [
            0.1,
            0.3
          ],
          "numerator": 14.0,
          "denominator": 60,
          "independent_query_groups": 20,
          "ci95": [
            0.027866481213768224,
            0.5189728183535235
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 6.0,
              "denominator": 20,
              "value": 0.3,
              "ci95": [
                0.1454772448676043,
                0.5189728183535235
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 2,
              "numerator": 2.0,
              "denominator": 20,
              "value": 0.1,
              "ci95": [
                0.027866481213768224,
                0.3010336452284873
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 3,
              "numerator": 6.0,
              "denominator": 20,
              "value": 0.3,
              "ci95": [
                0.1454772448676043,
                0.5189728183535235
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "n_refusal_proxy": {
          "mean": 0.06666666666666667,
          "range": [
            0.0,
            0.1
          ],
          "numerator": 2.0,
          "denominator": 30,
          "independent_query_groups": 10,
          "ci95": [
            0.0,
            0.4041500267952385
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 1.0,
              "denominator": 10,
              "value": 0.1,
              "ci95": [
                0.017876213095072896,
                0.4041500267952385
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 2,
              "numerator": 0.0,
              "denominator": 10,
              "value": 0.0,
              "ci95": [
                0.0,
                0.2775327998628892
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 3,
              "numerator": 1.0,
              "denominator": 10,
              "value": 0.1,
              "ci95": [
                0.017876213095072896,
                0.4041500267952385
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "complete": {
          "mean": 0.4111111111111111,
          "range": [
            0.16666666666666666,
            0.5333333333333333
          ],
          "numerator": 37.0,
          "denominator": 90,
          "independent_query_groups": 30,
          "ci95": [
            0.0733654237184855,
            0.6976761109230025
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 16.0,
              "denominator": 30,
              "value": 0.5333333333333333,
              "ci95": [
                0.36142299619873297,
                0.6976761109230025
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 2,
              "numerator": 5.0,
              "denominator": 30,
              "value": 0.16666666666666666,
              "ci95": [
                0.0733654237184855,
                0.3356435050641603
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 3,
              "numerator": 16.0,
              "denominator": 30,
              "value": 0.5333333333333333,
              "ci95": [
                0.36142299619873297,
                0.6976761109230025
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "partial": {
          "mean": 0.0,
          "range": [
            0.0,
            0.0
          ],
          "numerator": 0.0,
          "denominator": 90,
          "independent_query_groups": 30,
          "ci95": [
            0.0,
            0.11351339317396876
          ],
          "ci_method": "conservative envelope of per-repeat Wilson intervals; never pool repeat n",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 0.0,
              "denominator": 30,
              "value": 0.0,
              "ci95": [
                0.0,
                0.11351339317396876
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 2,
              "numerator": 0.0,
              "denominator": 30,
              "value": 0.0,
              "ci95": [
                0.0,
                0.11351339317396876
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            },
            {
              "repeat": 3,
              "numerator": 0.0,
              "denominator": 30,
              "value": 0.0,
              "ci95": [
                0.0,
                0.11351339317396876
              ],
              "ci_method": "Wilson, independent query groups within repeat"
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "body_token_f1": {
          "mean": 0.12555022543011124,
          "range": [
            0.06186905730375632,
            0.1573908094932887
          ],
          "numerator": 7.533013525806674,
          "denominator": 60,
          "independent_query_groups": 20,
          "ci95": [
            0.062176002466874276,
            0.1968575030682852
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 3.147816189865774,
              "denominator": 20,
              "value": 0.1573908094932887
            },
            {
              "repeat": 2,
              "numerator": 1.2373811460751263,
              "denominator": 20,
              "value": 0.06186905730375632
            },
            {
              "repeat": 3,
              "numerator": 3.147816189865774,
              "denominator": 20,
              "value": 0.1573908094932887
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "elapsed_seconds": {
          "mean": 13.660791810003058,
          "range": [
            10.248123286660606,
            19.27076882002099
          ],
          "numerator": 1229.4712629002752,
          "denominator": 90,
          "independent_query_groups": 30,
          "ci95": [
            9.187974277776407,
            18.112079192229753
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 343.9044996998273,
              "denominator": 30,
              "value": 11.463483323327576
            },
            {
              "repeat": 2,
              "numerator": 578.1230646006297,
              "denominator": 30,
              "value": 19.27076882002099
            },
            {
              "repeat": 3,
              "numerator": 307.44369859981816,
              "denominator": 30,
              "value": 10.248123286660606
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "attempts": {
          "mean": 7.444444444444445,
          "range": [
            6.8,
            7.933333333333334
          ],
          "numerator": 670.0,
          "denominator": 90,
          "independent_query_groups": 30,
          "ci95": [
            5.188888888888889,
            9.722222222222221
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 238.0,
              "denominator": 30,
              "value": 7.933333333333334
            },
            {
              "repeat": 2,
              "numerator": 204.0,
              "denominator": 30,
              "value": 6.8
            },
            {
              "repeat": 3,
              "numerator": 228.0,
              "denominator": 30,
              "value": 7.6
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        },
        "llm_calls": {
          "mean": 1.511111111111111,
          "range": [
            1.1333333333333333,
            1.7
          ],
          "numerator": 136.0,
          "denominator": 90,
          "independent_query_groups": 30,
          "ci95": [
            1.0222222222222221,
            1.9666666666666666
          ],
          "ci_method": "percentile bootstrap of whole query groups; 2000 draws, fixed seed",
          "per_repeat": [
            {
              "repeat": 1,
              "numerator": 51.0,
              "denominator": 30,
              "value": 1.7
            },
            {
              "repeat": 2,
              "numerator": 34.0,
              "denominator": 30,
              "value": 1.1333333333333333
            },
            {
              "repeat": 3,
              "numerator": 51.0,
              "denominator": 30,
              "value": 1.7
            }
          ],
          "interpretation": "estimate with CI",
          "repeated_runs_are_independent_questions": false
        }
      }
    }
  ],
  "new_local_commits": 4
}
```
