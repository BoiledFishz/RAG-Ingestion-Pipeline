"""Prepare offline independent-rating inputs from actual changed answers.

No online calls, model responses, invented facts, approvals or rating values.
Duplicate repetitions are grouped only when answer and fact hashes are equal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def build(root: Path, stage: str, *, partitions=('tune','held-out')) -> dict:
    sources={};items={};stage_folder=root/f'evals/project2-v1/{stage}'
    for partition in partitions:
        if partition=='held-out':
            receipt=read(stage_folder/'heldout_receipt.json')
            if receipt['status']!='completed' or receipt['heldout_repetitions_project2']!=3:
                raise ValueError('Held-out review is available only after the one stage invocation finishes')
        path=stage_folder/f'qa-{partition}/summary.json';summary=read(path)
        scored_path=path.with_name('scored.json');rows=read(scored_path)
        definitions_path=root/f'evals/protocol_v0/facts_{partition}.human_frozen.json'
        if sha(definitions_path)!=definitions_path.with_suffix('.json.sha256').read_text().split()[0]:
            raise ValueError('Human-frozen fact definitions changed')
        definitions={x['question_id']:x for x in read(definitions_path)['items']}
        pending={(x['question_id'],x['repeat']) for x in summary['required_facts']['unscored']}
        for p in (path,scored_path,definitions_path):sources[p.relative_to(root).as_posix()]=sha(p)
        for row in rows:
            if (row['question_id'],row['repeat']) not in pending:continue
            definition=definitions[row['question_id']]
            if not definition['human_approved']:raise ValueError('Unapproved fact definitions')
            body=(row.get('result') or {}).get('workers',{}).get('rag',{}).get('payload',{}).get('answer','')
            answer_hash=hashlib.sha256(body.encode('utf-8')).hexdigest()
            facts=definition['required_facts']
            fact_hash=hashlib.sha256(json.dumps(facts,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            key=(partition,row['question_id'],answer_hash,fact_hash)
            if key not in items:
                items[key]={'partition':partition,'question_id':row['question_id'],'question':definition['question'],
                            'answer_body':body,'answer_sha256':answer_hash,
                            'required_facts':facts,'definition_content_sha256':fact_hash,
                            'single_fact_exception':len(facts)==1,'observations':[],
                            'human_annotator':'','human_approved':False,
                            'human_scores':[{'fact_id':x['fact_id'],'score':None,'answer_quote':'','notes':''} for x in facts],
                            'independent_llm_status':'未执行','independent_llm_scores':[]}
            items[key]['observations'].append({'repeat':row['repeat'],'group_sha256':row['group_sha256']})
    return {'stage':stage,'status':'pending_independent_ratings','sources':sources,'items':list(items.values()),
            'scope':'offline fact rating only; gold never enters online Worker',
            'rules':['仅评答案正文；sources引用内容不计答案覆盖。','0=未覆盖/错误，1=部分覆盖，2=完整且正确。',
                     '1/2分引文必须是答案正文逐字片段；不修改已批准事实。','人工与不同于Qwen的模型独立评分；不先查看另一个评分。',
                     '分歧保留，不强行合并；单事实例外单独报告。','空白不是0分；完成评分后另存副本并填写真实评分者身份。']}


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--stage',required=True,choices=['ch12','ch13','ch14','ch15']);args=ap.parse_args()
    result=build(ROOT,args.stage);path=ROOT/f'evals/project2-v1/{args.stage}/independent_review/human_template.json'
    payload=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_text(encoding='utf-8')!=payload:raise ValueError('Existing review registration differs; do not rewrite')
    path.write_text(payload,encoding='utf-8');path.with_suffix('.json.sha256').write_text(sha(path)+'\n',encoding='utf-8')
    print(json.dumps({'path':str(path),'unique_answers':len(result['items']),
                      'answer_observations':sum(len(x['observations']) for x in result['items']),
                      'status':result['status'],'sha256':sha(path)},ensure_ascii=False))
