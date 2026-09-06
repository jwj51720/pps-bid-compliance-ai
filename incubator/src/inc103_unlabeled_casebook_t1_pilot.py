#!/usr/bin/env python3
"""Create a provenance-validated teacher casebook from unlabeled notices."""
from __future__ import annotations
import argparse,concurrent.futures,gzip,json,os
from pathlib import Path
from typing import Any
import requests
from dotenv import load_dotenv
import inc001_simple_joint24 as common
import inc081_teacher_full_context_calibration as calibration

ROOT=Path(__file__).resolve().parents[2];RAW=ROOT/'data/raw/open';CARDS=ROOT/'incubator/reference/dev_history/decision_cards_v6.json';MANIFEST=ROOT/'incubator/runs/inc080_teacher_pilot_manifest/manifest.jsonl';OUT=ROOT/'incubator/runs/inc103_unlabeled_casebook_t1_pilot';ITEMS=common.ITEMS
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf8').splitlines() if x]
def schema():
 e={'type':'object','additionalProperties':False,'required':['v','basis','quote'],'properties':{'v':{'type':'integer','enum':[0,1]},'basis':{'type':'string','maxLength':240},'quote':{'type':'string','maxLength':500}}}
 return {'type':'object','additionalProperties':False,'required':['case_signature','items'],'properties':{'case_signature':{'type':'string','maxLength':700},'items':{'type':'object','additionalProperties':False,'required':list(ITEMS),'properties':{i:e for i in ITEMS}}}}
def msg(r,c):
 core='\n\n'.join(f'[{i}|{x["item_name"]}]\n{x["prompt_text"]}' for i,x in c['cards'].items())
 s='''당신은 공공입찰 법령 판단의 정적 사례기록을 만드는 독립 검토자다. 제공된 metadata, 원문 전체, 항목카드만 사용한다. case_signature에는 공고유형·목적물·금액/계약방식·실제 참가자격·예외/사후의무를 짧게 사실로 기록한다. 각 항목은 적용대상→관찰 사실→예외→결론 순서로 독립 검토한다. v=1이면 quote는 판단을 뒷받침하는 원문의 변경 없는 연속 substring, v=0이면 quote는 빈 문자열이다. 키워드나 법령명만으로 결론을 만들지 않는다. JSON만 출력한다.'''
 u='\n\n'.join(['[항목카드]\n'+core,'[metadata]\n'+json.dumps(r['meta'],ensure_ascii=False,sort_keys=True),'[공고 원문 전체]\n'+calibration.render_documents(r)])
 return [{'role':'system','content':s},{'role':'user','content':u}]
def text(b):
 t=b.get('output_text');
 return t if isinstance(t,str) and t else ''.join(z.get('text','') for x in b.get('output',[]) if x.get('type')=='message' for z in x.get('content',[]) if z.get('type')=='output_text')
def call(key,m):
 p={'model':'gpt-5.6-luna','input':m,'max_output_tokens':8192,'store':False,'reasoning':{'effort':'high'},'text':{'format':{'type':'json_schema','name':'inc103_casebook','strict':True,'schema':schema()}}}
 try:
  q=requests.post('https://api.openai.com/v1/responses',headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},json=p,timeout=360);b=q.json();t=text(b)
  return {'success':bool(q.ok and t),'value':json.loads(t) if q.ok and t else None,'raw_response':t,'usage':b.get('usage',{}),'error':'' if q.ok and t else f'{q.status_code}:{b.get("status")}:{b.get("incomplete_details")}' }
 except Exception as e:return {'success':False,'error':f'{type(e).__name__}:{e}','raw_response':''}
def valid(v,r):
 if not isinstance(v,dict) or set(v)!={'case_signature','items'} or set(v['items'])!=set(ITEMS):raise ValueError('schema')
 src='\n'.join(x['text'] for x in r['docs']);out={};bad=[]
 for i,x in v['items'].items():
  if not isinstance(x,dict) or set(x)!={'v','basis','quote'} or x['v'] not in(0,1):raise ValueError(i)
  q=x['quote'].strip();ok=not x['v'] or bool(q) and q in src
  out[i]={'v':x['v'],'basis':x['basis'].strip(),'quote':q,'quote_valid':ok}
  if x['v'] and not ok:bad.append(i)
 return {'case_signature':v['case_signature'].strip(),'items':out},bad
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');a=ap.parse_args()
 if not a.run:raise SystemExit('pass --run')
 mani=jl(MANIFEST)[:16]
 with gzip.open(RAW/'train_unlabeled.jsonl.gz','rt',encoding='utf8') as h:records={x['id']:x for x in (json.loads(y) for y in h if y)}
 cards=json.loads(CARDS.read_text(encoding='utf8'));OUT.mkdir(parents=True,exist_ok=True);load_dotenv(ROOT/'.env');key=os.environ['OPENAI_API_KEY']
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  fs={pool.submit(call,key,msg(records[m['id']],cards)):m for m in mani}
  rows=[]
  for n,f in enumerate(concurrent.futures.as_completed(fs),1):
   x=f.result();m=fs[f];rid=m['id']
   if x['success']:
    try:x['record'],x['invalid_positive_quote_items']=valid(x.pop('value'),records[rid])
    except ValueError as e:x={'success':False,'error':str(e),'raw_response':x.get('raw_response','')}
   x.update({'id':rid,'input_sha256':m['input_sha256'],'model':'gpt-5.6-luna','reasoning_effort':'high','max_output_tokens':8192});rows.append(x);open(OUT/'responses.jsonl','a',encoding='utf8').write(json.dumps(x,ensure_ascii=False)+'\n');print(n,16,rid,x['success'],flush=True)
 ok=[x for x in rows if x['success']];pos=sum(x['record']['items'][i]['v'] for x in ok for i in ITEMS);bad=sum(len(x.get('invalid_positive_quote_items',[])) for x in ok);report={'requests':16,'success':len(ok),'positive_quotes':pos,'invalid_positive_quotes':bad,'valid_positive_quote_rate':(pos-bad)/pos if pos else 1};(OUT/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
