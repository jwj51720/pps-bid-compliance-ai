#!/usr/bin/env python3
"""High-reasoning, full-context case-report gate; no prediction merge."""
from __future__ import annotations

import argparse, concurrent.futures, csv, gzip, json, os, time
from pathlib import Path
from typing import Any
import requests
from dotenv import load_dotenv
import inc001_simple_joint24 as common
import inc081_teacher_full_context_calibration as calibration

ROOT=Path(__file__).resolve().parents[2]; RAW=ROOT/'data/raw/open'; CARDS=ROOT/'incubator/reference/dev_history/decision_cards_v6.json'; MANIFEST=ROOT/'incubator/runs/inc085_fact_ledger_adjudication_dev64/manifest.jsonl'; DIRECT=ROOT/'incubator/runs/inc088_openai_luna_high_full_dev_card/responses.jsonl'; OUT=ROOT/'incubator/runs/inc102_high_case_report_gate'
ITEMS=common.ITEMS
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf8').splitlines() if x]
def schema():
 e={'type':'object','additionalProperties':False,'required':['v','basis','quote'],'properties':{'v':{'type':'integer','enum':[0,1]},'basis':{'type':'string','maxLength':240},'quote':{'type':'string','maxLength':500}}}
 return {'type':'object','additionalProperties':False,'required':list(ITEMS),'properties':{i:e for i in ITEMS}}
def messages(r,cards):
 core='\n\n'.join(f'[{i}|{x["item_name"]}]\n{x["prompt_text"]}' for i,x in cards['cards'].items())
 system='''당신은 한국 공공입찰 법령 위반을 판정하는 독립 검토자다. 모든 공고 원문·metadata·판정카드만 사용한다. 각 항목을 적용대상→관찰된 공고 사실→수치/실제 참가자격/예외→결론 순서로 독립 검토한다. 키워드나 법령명만으로 단정하지 않는다. 각 항목에 v, 결론을 좌우한 짧은 basis, quote를 출력한다. v=1이면 quote는 반드시 판단을 뒷받침하는 공고 원문의 변경 없는 연속 부분문자열이어야 한다. v=0이면 quote는 빈 문자열이다. 부재형 항목은 적용대상 확인 뒤 공고 전체에서 필요한 조건이 없을 때만 1이다. 최종 JSON 하나만 출력한다.'''
 user='\n\n'.join(['[항목별 법령 판단 핵심]\n'+core,'[나라장터 metadata]\n'+json.dumps(r['meta'],ensure_ascii=False,sort_keys=True),'[공고 원문 전체]\n'+calibration.render_documents(r)])
 return [{'role':'system','content':system},{'role':'user','content':user}]
def text(body):
 t=body.get('output_text');
 if isinstance(t,str) and t:return t
 return ''.join(z.get('text','') for x in body.get('output',[]) if x.get('type')=='message' for z in x.get('content',[]) if z.get('type')=='output_text')
def call(key,msg):
 payload={'model':'gpt-5.6-luna','input':msg,'max_output_tokens':8192,'store':False,'reasoning':{'effort':'high'},'text':{'format':{'type':'json_schema','name':'inc102_case_report','strict':True,'schema':schema()}}}
 try:
  q=requests.post('https://api.openai.com/v1/responses',headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},json=payload,timeout=360);b=q.json();t=text(b)
  if q.ok and t:return {'success':True,'value':json.loads(t),'raw_response':t,'usage':b.get('usage',{})}
  return {'success':False,'error':f'{q.status_code}:{json.dumps({"status":b.get("status"),"incomplete":b.get("incomplete_details"),"error":b.get("error")},ensure_ascii=False)}','raw_response':t}
 except Exception as e:return {'success':False,'error':f'{type(e).__name__}:{e}','raw_response':''}
def validate(value,r):
 if not isinstance(value,dict) or set(value)!=set(ITEMS):raise ValueError('schema')
 source='\n'.join(x['text'] for x in r['docs']);out={};invalid=[]
 for i in ITEMS:
  x=value[i]
  if not isinstance(x,dict) or set(x)!={'v','basis','quote'} or x['v'] not in(0,1):raise ValueError(i)
  q=x['quote'].strip();valid=not x['v'] or bool(q) and q in source
  out[i]={'v':int(x['v']),'basis':x['basis'].strip(),'quote':q,'quote_valid':valid}
  if x['v'] and not valid:invalid.append(i)
 return out,invalid
def latest(p):
 d={}
 if not p.exists():return d
 for x in jl(p):
  if x.get('success'):d[x['id']]=x
 return d
def score(pred,gold):
 per=[]
 for i in ITEMS:
  tp=fp=fn=0
  for rid,x in pred.items():
   y=int(gold[rid][i]);v=int(x[i]);tp+=v==y==1;fp+=v==1 and not y;fn+=not v and y
  per.append({'item':i,'tp':tp,'fp':fp,'fn':fn,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0})
 return sum(x['f1'] for x in per)/24,per
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=('run','score'),default='run');ap.add_argument('--limit',type=int,default=16);a=ap.parse_args();manifest=jl(MANIFEST)[:a.limit]
 with gzip.open(RAW/'dev.jsonl.gz','rt',encoding='utf8') as h:records={x['id']:x for x in (json.loads(y) for y in h if y)}
 cards=json.loads(CARDS.read_text(encoding='utf8'));OUT.mkdir(parents=True,exist_ok=True)
 if a.mode=='run':
  load_dotenv(ROOT/'.env');key=os.environ['OPENAI_API_KEY'];done=latest(OUT/'checkpoint.jsonl');pending=[x for x in manifest if x['id'] not in done]
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
   fs={pool.submit(call,key,messages(records[m['id']],cards)):m['id'] for m in pending}
   for n,f in enumerate(concurrent.futures.as_completed(fs),1):
    x=f.result();rid=fs[f]
    if x['success']:
     try:x['report'],x['invalid_positive_quote_items']=validate(x.pop('value'),records[rid])
     except ValueError as e:x={'success':False,'error':str(e),'raw_response':x['raw_response']}
    x['id']=rid;open(OUT/'checkpoint.jsonl','a',encoding='utf8').write(json.dumps(x,ensure_ascii=False)+'\n');print(n,len(fs),rid,x['success'],flush=True)
 else:
  gold={x['id']:x for x in csv.DictReader((RAW/'dev_labels.csv').open(encoding='utf8'))};rows=latest(OUT/'checkpoint.jsonl');direct={x['id']:x['labels'] for x in jl(DIRECT)};m,per=score({r:x['report'] and {i:x['report'][i]['v'] for i in ITEMS} for r,x in rows.items()},gold);d,_=score({r:direct[r] for r in rows},gold);pos=sum(x['report'][i]['v'] for x in rows.values() for i in ITEMS);invalid=sum(len(x['invalid_positive_quote_items']) for x in rows.values());report={'success':len(rows),'case_report_macro':m,'direct_high_same_ids':d,'delta':m-d,'positive_quote_count':pos,'invalid_positive_quotes':invalid,'valid_positive_quote_rate':(pos-invalid)/pos if pos else 1,'per_item':per};(OUT/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
