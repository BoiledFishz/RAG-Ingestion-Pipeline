"""Create the narrow authorized revision, preserving v0.1/v0.2 bytes."""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'specs/project2/v0.2'
NEW = ROOT / 'specs/project2/v0.3'


def build() -> None:
    NEW.mkdir(parents=True, exist_ok=True)
    if (NEW / 'version_manifest.json').exists():
        raise ValueError('v0.3 already frozen; no regeneration allowed')
    protocol = json.loads((ROOT / 'evals/project2-v1/calibration_v03/protocol.json').read_text(encoding='utf-8'))
    for name, expected in protocol['protected_files'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    for file in OLD.iterdir():
        if file.is_file() and file.name not in {'approval_addendum.md','delta.md','delta.json','version_manifest.json','check_docs.py'}:
            shutil.copyfile(file, NEW / file.name)
    changes = []

    def text_change(name: str, before: str, after: str, category: str) -> None:
        path = NEW / name
        value = path.read_text(encoding='utf-8-sig')
        if before not in value:
            if after in value:
                return
            raise ValueError(f'No exact authorized span in {name}')
        assert value.count(before) == 1
        path.write_text(value.replace(before, after), encoding='utf-8')
        changes.append({'file': name, 'category': category, 'old': before, 'new': after})

    spec = (OLD / 'spec.md').read_text(encoding='utf-8-sig')
    before = spec[spec.index('<a id="s08">'):spec.index('<a id="s09">')]
    protocol_sha = hashlib.sha256((ROOT / 'evals/project2-v1/calibration_v03/protocol.json').read_bytes()).hexdigest()
    after = '''<a id="s08"></a>
## S08 默认 API 强制总预算（v0.3，授权 A）

CL-08 延迟与实际调用标定由用户2026-10-05授权；其余数据保留策略不变。生产默认仍为90秒/16依赖/6LLM，只有无删失、未触发熔断且冻结实测文件后才切换。DB单语句12秒、Worker25秒、模型单尝试30秒保持不变。

一次依赖尝试保持原口径：一个实际 SQL execute、事务 commit、HTTP send 或模型推理，在执行前原子预留；失败、取消、重试消耗尝试。executemany 若实际发出多条SQL则逐条计；真正的一个批量SQL只计一次。纯调度、解析、格式化不重复计数但耗时计入截止。没有为了降低数字而改计数规则。缓存命中仍计实际缓存SQL；不伪造模型调用。

默认 API 在验权/分派前建立同一绝对截止与总预算；两Worker、直接调用、异常、重试、取消、渲染和保存均受约束。预算耗尽时第N+1依赖、第L+1LLM不得启动，取消/终止在途任务，保留消费量和未知成本，按未改S07汇合。Resume不重置预算。旧MultiAgentVersion不变。

### S08.1 tune-only 完整集合标定

- 同一既有登记集合全部50条：compare/platform/identifier/version/entity各8条，no_answer_challenge10条；RAG单独和组合路径各3重复，共300次。顺序为路径、原登记样本顺序、重复1–3。不排除拒答、失败、慢题或挑战题，不根据答案/标签选择预算样本。held-out不读取。
- 保持冻结v0模型/提示词/阈值/索引/语料和计数口径；测量依赖分类、LLM次数、墙钟耗时、原响应/trace、异常及删失。已有持久缓存保留，逐次登记可解释的继承缓存状态，不声称首次必为冷缓存。按题聚类报告均值/范围/CI，三次重复不冒充150个独立问题。
- 离线测量包络：300秒/256依赖/64LLM，仅脚本构造，不能由API正文或用户Prompt授予，也不成为生产默认。这是本次A项为测量未截断尝试所需的观察范围，仍受30秒模型/12秒SQL等原本地超时约束。任何包络右删失不冻结上限；原始失败保留，不按成功子集取P95。
- P95采用nearest-rank：排序后第ceil(.95*n)个，每条路径单独计算，取两路径较大者。调用上限=ceil(1.25*ceil(P95))；墙钟=1.5*P95秒。依赖P95>32或LLM P95>12立即停止，不选新上限，不进入后续门禁/held-out；须先结构性精简RAG路径。
- 选择后冻结全部协议、原始记录、结果及SHA256；默认API只读取校验冻结预算，不能由普通配置或请求放大。AC12-01/15/16适用冻结N/L/T，保留故障注入与N+1/L+1不启动断言。
- 标定源：`evals/project2-v1/calibration_v03/protocol.json`，SHA256：`PROTOCOL_HASH`。结果与包绑定见`evals/project2-v1/calibration_v03/summary.json`和`frozen_manifest.json`；未产生时不得称已标定。State24小时/Trace7天决定不变。
- 阶段门禁通过前held-out累计保持0；锁定后仅阶段末一次（三重复），如实保留不佳结果，不用它调设计或再跑。

'''.replace('PROTOCOL_HASH', protocol_sha)
    text_change('spec.md', before, after, 'A_budget_protocol')
    text_change('spec.md', '规格 v0.2', '规格 v0.3', 'version_header')
    start = spec.index('**AC12-23**')
    end = spec.index('\n\n', start)
    after = '''**AC12-23（授权B）** 保留原场景ID与原问题P2-NOANSWER-01，拆成两个证据结论而不增加/删减场景：(a)门禁对预登记tune全部183条N原记录各3次（含180个不同原查询，保留重复记录、不删题）在组合路径执行，Supervisor必须与观察到的Worker状态对应的S07矩阵单元一致、无崩溃且run_id/trace/预算/错误可追溯；不要求RAG必为no_data。(b)拒答质量仅报告N题RAG no_data数/总数、Wilson及按问题聚类bootstrap95%CI、均值/范围和接受明细，failed/timeout单列、不冒充正确拒答。N标签仅用于离线队列登记和评分，不传给在线Worker。N针对官方候选范围，不证明全库无答案。原P2-NOANSWER-01实际有引用回答的历史样本保留；若不属于官方N队列则另作不可删补充样本，不冒充N分母。冻结v0结论不变，Project2不声称改善拒答质量。AC12-03双no_data Mock保持不变。登记及哈希同S08.1协议；必须先冻结队列再运行，不看输出改题。'''
    text_change('spec.md', spec[start:end], after, 'B_state_vs_quality')
    tasks = (OLD / 'tasks.md').read_text(encoding='utf-8')
    for tid, replacement, category in (
        ('T12-06', '默认API全预算强制；S08.1完整50题×3×两路径实测；P95公式、32/12熔断、删失识别、协议/结果/哈希冻结；第N+1/L+1不启动；内部可取消/计量', 'A_budget_task'),
        ('T12-09', '使用已登记原query/操作；成功有独立数据与技术证据；AC12-23(a)全部tune N×3观察态S07一致/可追溯门禁；(b)拒答质量报告/接受明细非门禁，保留原挑战，v0质量结论不变', 'B_state_task')):
        line = next(x for x in tasks.splitlines() if x.startswith('| ' + tid + ' |'))
        cells = line.split('|'); cells[3] = ' ' + replacement + ' '
        text_change('tasks.md', line, '|'.join(cells), category)
    cls = (OLD / 'clarifications.md').read_text(encoding='utf-8')
    line = next(x for x in cls.splitlines() if x.startswith('| CL-08 |'))
    cells = line.split('|')
    cells[3] = ' 按用户2026-10-05授权A，S08.1全50题×3×两路径标定，P95公式与32/12熔断；数据保留决定不变 '
    cells[4] = ' 原90/16/6在标定冻结前强制；DB12/25、模型30、State24小时/Trace7天不变；无删失后冻结参数及哈希 '
    cells[5] = ' 已获本次标定授权；实测状态由冻结结果给出 '
    text_change('clarifications.md', line, '|'.join(cells), 'A_CL08_measurement')
    # CSV changes are authored by the Artifact Tool builder, not this extractor.
    rows = list(csv.DictReader((OLD / 'acceptance_scenarios.csv').open(encoding='utf-8-sig', newline='')))
    for row in rows:
        old_row = dict(row)
        sid = row['scenario_id']
        if sid == 'AC12-01':
            row['setup'] += '；请求总预算采用S08.1无删失冻结的N/L/T；未冻结不得重跑门禁'
        elif sid == 'AC12-15':
            row['setup'] = '计时器/依赖计量Mock触及冻结N总尝试和L LLM；不调用真实模型；未冻结仍16/6'
            row['assertions'] = row['assertions'].replace('第17依赖或第7LLM不启动', '第N+1依赖或第L+1LLM不启动（N/L来自S08.1冻结值）')
        elif sid == 'AC12-16':
            row['setup'] += '；总预算使用S08.1冻结N/L/T，故障注入保持'
        elif sid == 'AC12-23':
            row['scenario'] = '真实N队列状态一致性门禁与拒答质量指标（分别报告）'
            row['setup'] = 'S08.1协议预登记全部tune N原记录×3；原P2-NOANSWER-01保留历史及补充样本；不读输出增删换题；在线Worker只有原问题和可信授权/预算，无标签/答案/目标'
            row['action'] = '正常组合入口执行全部N队列；由程序查S07观察态矩阵；分别输出(a)一致性门禁与(b)拒答质量/接受明细/CI；原挑战不删'
            row['expected_worker_states'] = 'RAG=observed;DB=observed'
            row['matrix_cell'] = 'S07[rag=observed,db=observed]'
            row['expected_overall_status'] = row['matrix_cell']
            row['assertions'] = 'S07[rag=observed,db=observed]；(a)每次实际六态组合唯一查36格S07，整体一致、无崩溃、可追溯；(b)no_data/总数及95%CI和接受明细，非门禁；原问题/历史结果保留；冻结v0结论不变，不声称改善拒答'
        edits = {k: {'old': old_row[k], 'new': v} for k,v in row.items() if old_row[k] != v}
        if edits:
            changes.append({'file': 'acceptance_scenarios.csv', 'scenario_id': sid, 'category': 'B_state_vs_quality' if sid == 'AC12-23' else 'A_budget_binding', 'cells': edits})
    (ROOT / 'audit/project2-v1/v03_scenarios_intermediate.json').write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    delta = {'from_version': 'v0.2', 'to_version': 'v0.3', 'authorization_date': '2026-10-05', 'changes': changes,
             'old_failure': {'category': 'dependency_attempt_limit', 'attempts': 16, 'llm_calls': 2, 'elapsed_seconds': 19.18484110001009,
                             'evidence': 'audit/project2-v1/native_gate_round2.json'}, 'attempt_definition_changed': False,
             'calibration_protocol_sha256': protocol_sha, 'calibration_result': 'evals/project2-v1/calibration_v03/summary.json'}
    (NEW / 'delta.json').write_text(json.dumps(delta, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['# v0.2 → v0.3 限定修订', '', '授权日期2026-10-05；仅A预算与B状态/质量拆分。原v0.1/v0.2字节不变。', '',
             'AC12-01的触发项为dependency_attempt_limit：16次依赖、2次LLM、19.184841秒，尚未触及6次LLM或90秒墙钟。证据：audit/project2-v1/native_gate_round2.json。',
             '计数口径不改：实际SQL/commit/HTTP/推理边界预留，executemany逐实际语句；批量一个语句只计一次。没有缩小数字的重新定义。', '',
             '| 文件/条目 | 旧值 | 新值与原因 | 证据 |', '| --- | --- | --- | --- |']
    for change in changes:
        name = change.get('scenario_id', change['category'])
        lines.append(f"| {change['file']} / {name} | 完整旧片段见delta.json | {change['category']}；用户A/B限定授权 | {delta['old_failure']['evidence'] if change['category'].startswith('A') else 'evals/project2-v1/calibration_v03/protocol.json'} |")
    lines += ['', '全部精确旧值/新值在delta.json保留。此时实测尚未结束；结果出现后只补实测值/冻结哈希，不凭候选值宣布完成。S07/场景集合/AC12-03/授权/范围/非目标/冻结协议/held-out规则不改。']
    (NEW / 'delta.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


if __name__ == '__main__':
    build()
