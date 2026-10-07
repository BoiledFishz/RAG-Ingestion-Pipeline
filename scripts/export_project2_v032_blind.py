"""Offline blind export of available historical answers; never claims post-v032 validation."""
from __future__ import annotations
import hashlib
import json
import random
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from project2_stage_eval import select_questions,online_question
from project2_v03_report import read,save,sha

def build():
    out=ROOT/'evals/project2-v1/blind_review_20261006'
    if out.exists():raise ValueError('Blind export already registered; preserve its order/hash')
    public=out/'public';private=out/'private';public.mkdir(parents=True);private.mkdir()
    seed=20261006
    sources=['evals/protocol_v0/runs/baseline-v0-quick/tune/runs.json',
             'evals/project2-v1/ch12/regression_repair1/scored.json',
             'evals/protocol_v0/facts_tune.human_frozen.json']
    facts_path=ROOT/sources[-1]
    if sha(facts_path)!=facts_path.with_suffix('.json.sha256').read_text().split()[0]:raise ValueError('Human fact definitions changed')
    facts={x['question_id']:x for x in read(facts_path)['items']}
    if not all(x['human_approved'] for x in facts.values()):raise ValueError('Not human approved')
    questions={x['record']['QUESTION_ID']:x for x in select_questions(ROOT,'tune')}
    plan={'seed':seed,'scope':'historical tune baseline and repair1 only; NOT post-v032 acceptance',
          'sources':{name:sha(ROOT/name) for name in sources},'order':'fixed-seed shuffle after grouping identical bodies',
          'empty_or_failed':'zero, excluded from agreement','LLM_calls':0,'heldout_bodies_read':False,
          'current_v032_status':'Native gate failed; no post-repair tune/held-out answers exist',
          'public_fields':['blind_id','question','answer_body','required_facts','ratings','reviewer','review_date','question_judgment'],
          'private_mapping':'private/key.json separately; do not open before review',
          'baseline_and_repair_answers_never_modified':True}
    save(private/'export_plan.json',plan)
    groups={};zero=[];observations=0
    for system,path in [('baseline_v0',sources[0]),('repair1_pre_v032',sources[1])]:
        for row in read(ROOT/path):
            qid=row['question_id']
            if qid not in questions:continue
            q=questions[qid]['record'];observations+=1
            if system=='baseline_v0':
                native=(row.get('native') or {}).get('run') or {}
                body=native.get('response',{}).get('answer','');status=native.get('trace',{}).get('status','failed')
            else:
                rag=(row.get('result') or {}).get('workers',{}).get('rag',{})
                body=rag.get('payload',{}).get('answer','');status=rag.get('status','failed')
            metadata={'system':system,'partition':'tune','question_id':qid,'repeat':row['repeat'],'status':status,
                      'answer_sha256':hashlib.sha256(body.encode()).hexdigest(),'label':q['ANSWERABLE'],
                      'source_file':path,'source_sha256':sha(ROOT/path),'current_v032':False}
            if not body.strip() or status in {'failed','timeout','invalid_evidence'}:
                zero.append({**metadata,'assigned_fact_score':0,'agreement_eligible':False,'reason':'empty_or_failed'});continue
            key=(qid,metadata['answer_sha256'])
            if key not in groups:groups[key]={'body':body,'qid':qid,'observations':[]}
            groups[key]['observations'].append(metadata)
    order=list(groups.values());random.Random(seed).shuffle(order)
    items=[];keys=[];markdown=['# 盲评包','',
      '请勿打开另存的 key.json。只依据答案正文逐条评分：0=未覆盖或错误，1=部分覆盖，2=完整且正确。',
      '正分需摘录正文中的原句；不得把来源附录、题目或模型信心当作答案。保持分歧，不强行合并。',
      '请填写 blind_review.json 的 ratings、reviewer 和 review_date；没有事实条目的题填写 question_judgment（完整/部分/拒答/错误）及备注。',
      '单事实例外单独报告，不进入主事实覆盖均值。技术产品版本号保留；评测系统身份信息未提供。','']
    for index,group in enumerate(order,1):
        bid=f'B{index:03d}';definition=facts.get(group['qid'])
        record=questions[group['qid']]['record']
        if record['ANSWERABLE']=='Y' and definition is None:raise ValueError('Missing human-frozen definition')
        required=definition['required_facts'] if definition else []
        public_facts=[{k:f[k] for k in ('fact_id','text','category','reference_quote') if k in f} for f in required]
        item={'blind_id':bid,'question':online_question(record)['query'],'answer_body':group['body'],
              'required_facts':public_facts,'ratings':[{'fact_id':f['fact_id'],'score':None,'answer_quote':'','comment':''} for f in required],
              'reviewer':'','review_date':'','question_judgment':{'status':None,'comment':''}}
        items.append(item);keys.append({'blind_id':bid,'observations':group['observations'],
              'facts_source_sha256':sha(facts_path),'single_fact_exception':len(required)==1})
        markdown+=['## '+bid,'',item['question'],'','答案正文：','',group['body'],'','| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |','| --- | --- | --- | --- |']
        for fact in public_facts:markdown.append('| '+fact['fact_id']+' | '+fact['text'].replace('|','\\|').replace('\n',' ')+' |  |  |')
        markdown+=['','评审人：________　日期：________　整题判断：________','']
    save(public/'blind_review.json',{'instructions':'0=未覆盖或错误；1=部分；2=完整正确；正分须引用正文；不得查看key或既有评分。','items':items})
    (public/'blind_review.md').write_text('\n'.join(markdown)+'\n',encoding='utf-8')
    save(private/'key.json',{'plan_sha256':sha(private/'export_plan.json'),'keys':keys,'automatic_zero':zero})
    forbidden={'system','partition','version','question_id','old_score','label','source_file'}
    assert all(not forbidden&item.keys() for item in items)
    assert all(item['answer_body'].strip() for item in items)
    assert sum(len(x['observations']) for x in keys)+len(zero)==observations
    receipt={'status':'exported_historical_only','current_v032_acceptance':False,
             'nonempty_answer_groups':len(items),'nonempty_answer_observations':sum(len(x['observations']) for x in keys),
             'auto_zero_observations':len(zero),'all_observations':observations,'LLM_calls':0,'scoring_status':'待盲评',
             'public_json':(public/'blind_review.json').relative_to(ROOT).as_posix(),
             'public_markdown':(public/'blind_review.md').relative_to(ROOT).as_posix(),
             'key_file':(private/'key.json').relative_to(ROOT).as_posix(),
             'files':{p.relative_to(ROOT).as_posix():sha(p) for p in [public/'blind_review.json',public/'blind_review.md',private/'key.json',private/'export_plan.json']}}
    save(ROOT/'audit/project2-v1/v032_blind_export_receipt.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in {'files','key_file'}},ensure_ascii=False))

if __name__=='__main__':build()
