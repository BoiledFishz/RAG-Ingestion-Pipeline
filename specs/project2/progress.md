# Project 2 自动执行续跑记录

程序更新时间：2026-10-06T22:46:23.072634+00:00

当前阶段：Chap12；生效规格v0.3.1；状态：stopped_s14_acceptance

分支：codex/project2-ch12；基准提交：74601e4a587ce70d6d9d82012bc5f42b42a0501d

标定批次2：300/300；批次1保留，未用于决策。协议/记录：evals/project2-v1/calibration_v031；日志audit/project2-v1/v031_calibration.log。

真实组合子门禁进度：{'repair_round': 1, 'requests': 555, 'expected': 555, 'failed_observations': 0, 'records': 'audit/project2-v1/v031_native_requests_round1.jsonl'}。

held-out累计阶段/重复：1/3；完整门禁通过前不得使用。

停止原因：批准S14未满足：tune原成功对照7题退化；80份答案仍缺独立双评分。工程门禁通过，质量未验收；本阶段held-out已消费一次，不改配置重跑，不把阶段记为完整通过或推进Chap13。

已冻结批次不得改写或逐条补测；批次2仅睡眠无效才自动独立批次3，其他删失停止。防睡眠请求在运行器自身线程，5秒心跳；不改系统设置、不安装。

原v0.1/v0.2/v0.3和批准v0.3.1冻结文件不可修改。两轮修复上限、门禁、场景及held-out规则不变。Chap16/远端/付费/系统安装不在范围。
