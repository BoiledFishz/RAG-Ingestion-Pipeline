"""One-shot narrowly authorized spec supplement; never overwrite approved files."""
from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'audit/project2-course-completion-20261007'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    old = ROOT / 'specs/project2/v0.3.3'
    new = ROOT / 'specs/project2/v0.3.4'
    if new.exists():
        raise FileExistsError('Never replace a specification version')
    shutil.copytree(old, new, ignore=shutil.ignore_patterns('__pycache__'))
    (new / 'version_manifest.json').unlink()
    proposal = AUDIT / 'component_expectation_proposal_v2.json'
    data = json.loads(proposal.read_text(encoding='utf-8'))
    differences = data['differences']
    assert len(differences) == 1
    previous = ROOT / 'audit/project2-v1/preflight_report.json'
    expectations = json.loads(previous.read_text(encoding='utf-8'))['sample_measurements']
    revised = json.loads(json.dumps(expectations))
    for item in differences:
        before = expectations[item['sample_id']]
        assert before == item['frozen_expectation']
        a, b = item['independent_counts']
        revised[item['sample_id']] = {
            'predicates': item['independent_literal_predicates'], 'counts': [a, b],
            'intersection': item['intersection'], 'delta_a_minus_b': a-b,
            'union': a+b-item['intersection'], 'measurement_complete': True,
            'not_worker_execution': True,
        }
    sidecar = {'version': 'project2-data-expectations-v034',
               'source_file': previous.relative_to(ROOT).as_posix(), 'source_sha256': sha(previous),
               'independent_proof': proposal.relative_to(ROOT).as_posix(), 'independent_proof_sha256': sha(proposal),
               'sample_measurements': revised, 'official_fields_modified': False,
               'historical_results_regraded': False}
    (new / 'data_expectations.json').write_text(json.dumps(sidecar,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    anchor = '<a id="s02"></a>'
    addition = '''### S01.2 v0.3.4 字面组件与独立数据预期补充（2026-10-07 实现前授权）

本补充只明确既有查询侧组件识别，不改变原50任务、抽样、种子、问题字符串或任务类别。统计槽位读取原 query 的等长视图：协议URL及www地址用等长空白屏蔽，URL内路径/版本不作为产品槽位；原请求与RAG输入不变。已登记产品优先；比较缺少两组时允许原文组件跨度补足：2–12位大写缩写、含内部大写的名称，或紧邻字面版本的首字母大写名称。排除诊断/语法标记 ERROR/WARNING/INFO/ANSWER/QUESTION/HTTP/HTTPS/URL/SQL/XML/IP/ID/QID/SSL/INSTALLATION/EXIT/REQUESTED/TERMINATION/REASON/CODE/API/NET。版本在最近组件之后32字符内且不得跨下一实体；IP/XML数值不作为版本，不补别名、不读取答案、标签或目标ID。

仅对旧独立复算未覆盖的明确组件比较增加版本化数据预期，见 data_expectations.json。期望数全部来自独立脚本对官方全文库的只读COUNT与INTERSECT，未复用Worker或目录构建代码。该脚本先排除URL与语法标记再取原文组件/版本；第1版误把API当组件的草稿弃用并保留。新版同一原请求两组计数245与79、交集2、差值166；文档数不能解释为支持状态、故障率或工单量。旧预期、旧成绩保留，不追溯重评为新版成功。

S07/S14、场景集合、权限/非目标、CL决定、19次依赖/6次LLM/90秒、累计执行记账、900秒存活上限、held-out规则完全不变。本补充为用户直接批准的最小澄清，不代填旧审阅日期或人工签名。门禁和事实质量仍需程序及对应真实证据判断。

'''
    text = (old / 'spec.md').read_text(encoding='utf-8')
    assert text.count(anchor)==1
    (new / 'spec.md').write_text(text.replace(anchor,addition+anchor),encoding='utf-8')
    protected = {p.relative_to(ROOT).as_posix():sha(p)
                 for directory in (ROOT/'specs/project2').iterdir() if directory.is_dir() and directory != new
                 for p in directory.iterdir() if p.is_file()}
    delta = {'from_version':'v0.3.3','to_version':'v0.3.4','authorization_date':'2026-10-07',
             'protected_files':protected,'changes':[
                 {'file':'spec.md','old':anchor,'new':addition+anchor,'category':'literal_component_clarification'},
                 {'file':'data_expectations.json','category':'independent_data_expectation',
                  'sample_keys':[x['sample_id'] for x in differences], 'proof_sha256':sha(proposal)}]}
    (new / 'delta.json').write_text(json.dumps(delta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (new / 'delta.md').write_text('# v0.3.3 → v0.3.4\n\n2026-10-07 用户直接批准后、补充实现前登记。\n\n'
        '- 规则：原规格允许明示组件但独立复算未覆盖；明确字面组件、URL排除及语法标记排除，原抽样/任务不变。\n'
        '- 数据：原澄清/未测量 → 独立官方全文COUNT 245/79、INTERSECT 2、差值166，仅新增sidecar，不覆盖历史预期与结果。\n\n'
        '独立证据：audit/project2-course-completion-20261007/component_expectation_proposal_v2.json。第1版API误选草稿原样保留且弃用。\n\n'
        'S07、S14、19/6/90、权限、CL、held-out及全部旧文件不变。\n',encoding='utf-8')
    (new / 'approval_addendum.md').write_text('# v0.3.4 用户直接授权\n\n日期：2026-10-07，America/Los_Angeles；本补充实现前授权。\n\n'
        '用户原文：**批准这项最小规则与数据预期补充**。\n\n'
        '授权所指：`audit/project2-course-completion-20261007/component_rule_revision_proposal.md`中仅字面组件识别与独立数据预期的最小修订。'
        '保留原题、50任务、旧成绩、S07/S14、19/6/90预算及held-out规则。所有旧批准文件保持不变，不代填旧审阅栏。\n\n'
        '提案 SHA256：`'+sha(AUDIT/'component_rule_revision_proposal.md')+'`。\n'
        '独立复算 v2 SHA256：`'+sha(proposal)+'`。\n',encoding='utf-8')


if __name__ == '__main__':
    main()
