# v0.3.1 → v0.3.2

2026-10-06用户在实现之前授权，仅恢复期限记账：累计执行片段、不计停机；新增900秒存活上限。

- {"file": "spec.md", "category": "recovery_time_accounting_only", "old": "<a id=\"s09\"></a>", "new": "### S08.3 v0.3.2 恢复期限累计执行记账（2026-10-06 实现前授权）\n\n本段仅替代恢复时的期限记账语义；已冻结数值为19次依赖、6次LLM、37.941018秒（摘要显示37.941秒），数值、标定原记录/公式/熔断不变。请求执行片段从默认API预算建立到响应/中断清理结束，按单调时钟累计；恢复的新片段只获得原执行总额减去已消费时间的余额，不把整额重置。停止服务、重新启动进程与依赖就绪/全量索引加载但尚未恢复该请求的时间不计执行消费。片段内等待模型、SQL、重试、元数据持久化、渲染和取消仍计入。\n\n消费量在尝试预留、节点结果及结束/中断时持久化，执行中以0.25秒周期保存时间心跳。非正常终止未确认的最后一个周期保守计入消费，不将它算作0；正常关闭保存实际结束时间。记录每个片段及其消费，跨恢复求和；依赖/LLM累计计数和结果不清零。瞬时绝对截止是余额在当前片段的执行边界，不能再被误当成跨停机不变的截止时间。\n\n新增运行存活上限900秒（15分钟暂定值），从首次运行created_at算起，含停机；该值在任何v0.3.2真实门禁前登记并记录SHA256。它与State保留24小时、Trace保留7天不同，不改变CL决定。累计执行超限或存活超限时明确timeout或failed；不静默新建运行，不清零计数。原AC13-02的拒绝门禁保持，改为检查累计超限/存活超限及原损坏/版本/权限边界。\n\n其余S07/S14、场景集合/原查询、门禁成功条件、授权/非目标、CL决定及held-out冻结协议不变。第13章确认性held-out调用与tune冒烟、旧评分作废及盲评导出是本次执行授权，记录在批准附录及执行账本，不改评测协议。\n\n<a id=\"s09\"></a>"}
- {"file": "acceptance_scenarios.csv", "scenario_id": "AC13-01", "column": "setup", "old": "合法请求中间结果与预算已持久化；尚未到绝对截止", "new": "合法请求中间结果、尝试及累计执行时间已持久化；执行余额为正且未到900秒存活上限", "category": "recovery_time_accounting_only"}
- {"file": "acceptance_scenarios.csv", "scenario_id": "AC13-02", "column": "setup", "old": "隔离Runtime副本的绝对截止时间已过期；重新验权合法但不得恢复调用。损坏/版本错误另用明确failed/failed→failed子案例，不与本行超时期望混写。", "new": "隔离Runtime副本的累计执行时间已超限，或900秒存活上限已过期；重新验权合法但不得恢复调用。损坏/版本错误另用明确failed/failed→failed子案例，不与本行超时期望混写。", "category": "recovery_time_accounting_only"}
- {"file": "acceptance_scenarios.csv", "scenario_id": "AC13-02", "column": "assertions", "old": "S07[rag=timeout,db=timeout]=timeout；未知/非法显式失败；超过原截止不能重置预算；不静默创建新运行", "new": "S07[rag=timeout,db=timeout]=timeout；未知/非法显式失败；累计超限或900秒存活过期不能重置预算；不静默创建新运行", "category": "recovery_time_accounting_only"}

原19/6/37.941018阈值、S07、S14、门禁成功条件及其他CL决定不变。旧版本逐文件哈希见delta.json。
