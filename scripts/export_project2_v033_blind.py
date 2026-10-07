"""Offline blind export of final v033 answers only; requires completed confirmatory receipt."""
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
    out=ROOT/'evals/project2-v1/blind_review_v033_final'
    if out.exists():raise ValueError('Blind export already registered; preserve its order/hash')
    public=out/'public';private=out/'private'
    seed=20261006
    receipt=read(ROOT/'evals/project2-v1/ch13_v033/heldout_receipt.json')
    if not receipt or receipt['status']!='completed':raise ValueError('Final confirmatory run incomplete; do not export historical answers')
    stage=read(ROOT/'evals/project2-v1/ch13_v033/stage.plan.json')
    for path,digest in stage['online_files'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Final code changed since confirmatory run')
    sources=['evals/project2-v1/ch13_v033/qa-tune/scored.json','evals/project2-v1/ch13_v033/qa-held-out/scored.json',
             'evals/protocol_v0/facts_tune.human_frozen.json','evals/protocol_v0/facts_held-out.human_frozen.json']
    facts={};questions={};fact_sources={}
    for partition in ('tune','held-out'):
        fp=ROOT/f'evals/protocol_v0/facts_{partition}.human_frozen.json'
        if sha(fp)!=fp.with_suffix('.json.sha256').read_text().split()[0]:raise ValueError('Human fact definitions changed')
        for x in read(fp)['items']:
            if not x['human_approved']:raise ValueError('Not human approved')
            facts[x['question_id']]=x;fact_sources[x['question_id']]=sha(fp)
        split=read(ROOT/'splits.json')['partitions'][partition];path=ROOT/split['file']
        if sha(path)!=split['sha256']:raise ValueError('Frozen partition changed')
        for x in read(path):questions[x['record']['QUESTION_ID']]=x
    plan={'seed':seed,'scope':'final v033 tune and once-only confirmatory held-out; no old pack or historical answer reuse',
          'sources':{name:sha(ROOT/name) for name in sources},'order':'fixed-seed shuffle after grouping identical bodies',
          'empty_or_failed':'zero, excluded from agreement','LLM_calls':0,'heldout_processing':'fixed offline export only, never design/diagnosis; user authorized',
          'current_v033_status':'final source hashes verified; confirmatory receipt completed',
          'public_fields':['blind_id','question','answer_body','required_facts','ratings','reviewer','review_date','question_judgment'],
          'private_mapping':'private/key.json separately; do not open before review',
          'baseline_and_repair_answers_never_modified':True}
    groups={};zero=[];observations=0
    for partition,path in [('tune',sources[0]),('held-out',sources[1])]:
        for row in read(ROOT/path):
            qid=row['question_id']
            if qid not in questions:continue
            q=questions[qid]['record'];observations+=1
            rag=(row.get('result') or {}).get('workers',{}).get('rag',{})
            body=rag.get('payload',{}).get('answer','');status=rag.get('status','failed')
            metadata={'system':'project2_v033_final','partition':partition,'question_id':qid,'repeat':row['repeat'],'status':status,
                      'answer_sha256':hashlib.sha256(body.encode()).hexdigest(),'label':q['ANSWERABLE'],
                      'source_file':path,'source_sha256':sha(ROOT/path),'current_v033':True}
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
              'facts_source_sha256':fact_sources.get(group['qid']),'single_fact_exception':len(required)==1})
        markdown+=['## '+bid,'','```text',item['question'],'```','','答案正文：','','```text',group['body'],'```','','| 事实 | 定义 | 0/1/2 | 正文引文 / 备注 |','| --- | --- | --- | --- |']
        for fact in public_facts:markdown.append('| '+fact['fact_id']+' | '+fact['text'].replace('|','\\|').replace('\n',' ')+' |  |  |')
        markdown+=['','评审人：________　日期：________　整题判断：________','']
    forbidden={'system','partition','version','question_id','old_score','label','source_file'}
    assert all(not forbidden&item.keys() for item in items)
    assert all(item['answer_body'].strip() for item in items)
    assert sum(len(x['observations']) for x in keys)+len(zero)==observations
    # Validate the complete final dataset before creating a reviewable package.
    # Rejected premature exports must leave no directory that blocks final export.
    public.mkdir(parents=True);private.mkdir()
    save(private/'export_plan.json',plan)
    save(public/'blind_review.json',{'instructions':'0=未覆盖或错误；1=部分；2=完整正确；正分须引用正文；不得查看key或既有评分。','items':items})
    (public/'blind_review.md').write_text('\n'.join(markdown)+'\n',encoding='utf-8')
    save(private/'key.json',{'plan_sha256':sha(private/'export_plan.json'),'keys':keys,'automatic_zero':zero})
    receipt={'status':'exported_final_confirmatory','current_v033_acceptance':False,'budget_seconds':90,
             'nonempty_answer_groups':len(items),'nonempty_answer_observations':sum(len(x['observations']) for x in keys),
             'auto_zero_observations':len(zero),'all_observations':observations,'LLM_calls':0,'scoring_status':'待盲评',
             'public_json':(public/'blind_review.json').relative_to(ROOT).as_posix(),
             'public_markdown':(public/'blind_review.md').relative_to(ROOT).as_posix(),
             'key_file':(private/'key.json').relative_to(ROOT).as_posix(),
             'files':{p.relative_to(ROOT).as_posix():sha(p) for p in [public/'blind_review.json',public/'blind_review.md',private/'key.json',private/'export_plan.json']}}
    save(ROOT/'audit/project2-v1/v033_blind_export_receipt.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in {'files','key_file'}},ensure_ascii=False))

if __name__=='__main__':build()
