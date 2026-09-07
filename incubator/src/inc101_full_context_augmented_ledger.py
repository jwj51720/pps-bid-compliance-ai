#!/usr/bin/env python3
"""Two-pass fact ledger with full notice retained for final adjudication."""
from __future__ import annotations

import argparse, concurrent.futures, csv, gzip, json, os, time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

import inc001_simple_joint24 as common
import inc081_teacher_full_context_calibration as calibration

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'data/raw/open'; CARDS=ROOT/'incubator/reference/dev_history/decision_cards_v6.json'
MANIFEST=ROOT/'incubator/runs/inc085_fact_ledger_adjudication_dev64/manifest.jsonl'
DIRECT=ROOT/'incubator/runs/inc088_openai_luna_high_full_dev_card/responses.jsonl'
OUT=ROOT/'incubator/runs/inc101_full_context_augmented_ledger_gate'
GROUPS=('procurement_type','product_applicability','price_and_amount','bidder_eligibility','direct_production','sme_competition','region_and_industry','exception_or_postaward','dates_and_schedule')

def jsonl(p:Path)->list[dict[str,Any]]: return [json.loads(x) for x in p.read_text(encoding='utf8').splitlines() if x]
def docs(r:dict[str,Any])->str:return calibration.render_documents(r)
def ledger_schema()->dict[str,Any]:
 e={'type':'object','additionalProperties':False,'required':['fact','quote'],'properties':{'fact':{'type':'string','maxLength':600},'quote':{'type':'string','maxLength':500}}}
 return {'type':'object','additionalProperties':False,'required':list(GROUPS),'properties':{x:e for x in GROUPS}}
def label_schema()->dict[str,Any]:return {'type':'object','additionalProperties':False,'required':list(common.ITEMS),'properties':{x:{'type':'integer','enum':[0,1]} for x in common.ITEMS}}
def core(c:dict[str,Any])->str:return '\n\n'.join(f'[{i}|{x["item_name"]}]\n{x["prompt_text"]}' for i,x in c['cards'].items())
def extract_msg(r,c):
 s='''당신은 공공입찰 공고의 사실 기록관이다. 위반 여부나 v번호의 결론을 절대 판단하지 않는다. 각 typed group에 원문에서 관찰되는 사실만 요약하고, 비어 있지 않은 fact에는 그것을 뒷받침하는 변경 없는 원문 연속 substring quote를 붙인다. 직접생산, 중소기업자간 경쟁, 일반 중소기업 언급, 낙찰 후 의무/안내를 서로 다른 사실로 기록한다. 원문 근거가 없으면 fact와 quote를 모두 빈 문자열로 둔다. JSON만 출력한다.'''
 u='[판정카드]\n'+core(c)+'\n\n[metadata]\n'+json.dumps(r['meta'],ensure_ascii=False,sort_keys=True)+'\n\n[공고 원문 전체]\n'+docs(r)
 return [{'role':'system','content':s},{'role':'user','content':u}]
def judge_msg(r,c,ledger):
 s='''당신은 한국 공공입찰 법령 위반을 판정하는 독립 검토자다. 원문 전체가 최종 근거이고 typed fact ledger는 원문 탐색을 돕는 보조색인이다. 각 v는 독립 법적 요건이다. 특히 직접생산 조건은 그 자체로 중소기업자간 경쟁 조건이 아니며, 일반 중소기업 언급·낙찰후 의무·안내도 참가자격 제한이 아니다. 적용대상, 금액/계약방식, 실제 참가자격, 예외를 항목별로 함께 확인한다. ledger가 비어 있어도 원문을 직접 검사하며, ledger의 요약이 원문과 충돌하면 원문을 따른다. 최종 24개 0/1 JSON만 출력한다.'''
 u='[판정카드]\n'+core(c)+'\n\n[metadata]\n'+json.dumps(r['meta'],ensure_ascii=False,sort_keys=True)+'\n\n[typed 사실 ledger]\n'+json.dumps(ledger,ensure_ascii=False,sort_keys=True)+'\n\n[공고 원문 전체]\n'+docs(r)
 return [{'role':'system','content':s},{'role':'user','content':u}]
def get_text(b):
 t=b.get('output_text')
 if isinstance(t,str) and t:return t
 return ''.join(z.get('text','') for x in b.get('output',[]) if x.get('type')=='message' for z in x.get('content',[]) if z.get('type')=='output_text')
def call(key,msg,cap,schema,name,effort):
 p={'model':'gpt-5.6-luna','input':msg,'max_output_tokens':cap,'store':False,'reasoning':{'effort':effort},'text':{'format':{'type':'json_schema','name':name,'strict':True,'schema':schema}}}
 err='unknown'; raw=''
 for n in range(2):
  try:
   q=requests.post('https://api.openai.com/v1/responses',headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},json=p,timeout=300);b=q.json();raw=get_text(b)
   if q.ok and raw:return {'success':True,'value':json.loads(raw),'raw_response':raw,'usage':b.get('usage',{})}
   err=f'{q.status_code}:{json.dumps({"status":b.get("status"),"incomplete":b.get("incomplete_details"),"error":b.get("error")},ensure_ascii=False)}'
  except Exception as e:err=f'{type(e).__name__}:{e}'
  time.sleep(2**n)
 return {'success':False,'error':err,'raw_response':raw}
def validate_ledger(v,r):
 source='\n'.join(d['text'] for d in r['docs']); cleaned={}; invalid=[]
 for g in GROUPS:
  x=v.get(g,{}) if isinstance(v,dict) else {}; fact=str(x.get('fact','')).strip() if isinstance(x,dict) else ''; quote=str(x.get('quote','')).strip() if isinstance(x,dict) else ''
  if fact and quote and quote in source and len(quote)<=500:cleaned[g]={'fact':fact,'quote':quote}
  elif not fact and not quote:cleaned[g]={'fact':'','quote':''}
  else:cleaned[g]={'fact':'','quote':''};invalid.append(g)
 return cleaned,invalid
def latest(p):
 d={}
 if not p.exists():return d
 for x in jsonl(p):
  if x.get('success'):d[x['id']]=x
 return d
def f1(pred,gold):
 rows=[]
 for i in common.ITEMS:
  tp=fp=fn=0
  for rid,x in pred.items():
   a=int(gold[rid][i]);v=int(x[i]);tp+=v==a==1;fp+=v==1 and a==0;fn+=v==0 and a==1
  rows.append({'item':i,'tp':tp,'fp':fp,'fn':fn,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0})
 return sum(x['f1'] for x in rows)/24,rows
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=('run','score'),default='run');ap.add_argument('--limit',type=int,default=16);args=ap.parse_args()
 manifests=jsonl(MANIFEST)[:args.limit]
 with gzip.open(RAW/'dev.jsonl.gz','rt',encoding='utf8') as h:rs={r['id']:r for r in (json.loads(x) for x in h if x)}
 cards=json.loads(CARDS.read_text(encoding='utf8'));OUT.mkdir(parents=True,exist_ok=True)
 if args.mode=='run':
  load_dotenv(ROOT/'.env');key=os.environ['OPENAI_API_KEY'];ex_path=OUT/'extract.jsonl'; old=latest(ex_path); pending=[m for m in manifests if m['id'] not in old]
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
   fs={pool.submit(call,key,extract_msg(rs[m['id']],cards),4096,ledger_schema(),'inc101_ledger','medium'):m['id'] for m in pending}
   for n,f in enumerate(concurrent.futures.as_completed(fs),1):
    x=f.result();rid=fs[f]
    if x['success']:x['ledger'],x['invalid_groups']=validate_ledger(x.pop('value'),rs[rid])
    x.update({'id':rid,'stage':'extract'});open(ex_path,'a',encoding='utf8').write(json.dumps(x,ensure_ascii=False)+'\n');print('extract',n,len(fs),rid,x['success'],flush=True)
  ledgers=latest(ex_path);ad_path=OUT/'adjudicate.jsonl';old=latest(ad_path);pending=[m for m in manifests if m['id'] in ledgers and m['id'] not in old]
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
   fs={pool.submit(call,key,judge_msg(rs[m['id']],cards,ledgers[m['id']]['ledger']),4096,label_schema(),'inc101_labels','high'):m['id'] for m in pending}
   for n,f in enumerate(concurrent.futures.as_completed(fs),1):
    x=f.result();rid=fs[f]
    if x['success'] and (set(x['value'])!=set(common.ITEMS) or any(x['value'][i] not in (0,1) for i in common.ITEMS)):x={'success':False,'error':'bad labels'}
    elif x['success']:x['labels']=x.pop('value')
    x.update({'id':rid,'stage':'adjudicate'});open(ad_path,'a',encoding='utf8').write(json.dumps(x,ensure_ascii=False)+'\n');print('judge',n,len(fs),rid,x['success'],flush=True)
 else:
  gold={r['id']:r for r in csv.DictReader((RAW/'dev_labels.csv').open(encoding='utf8'))}; ex=latest(OUT/'extract.jsonl'); ad=latest(OUT/'adjudicate.jsonl'); direct={x['id']:x['labels'] for x in jsonl(DIRECT)};ids=[m['id'] for m in manifests if m['id'] in ex and m['id'] in ad]; m,items=f1({x:ad[x]['labels'] for x in ids},gold);d,_=f1({x:direct[x] for x in ids},gold);non=sum(bool(ex[x]['ledger'][g]['fact']) for x in ids for g in GROUPS);report={'paired':len(ids),'augmented_macro':m,'direct_high_same_ids':d,'delta':m-d,'ledger_nonempty_rate':non/(len(ids)*len(GROUPS)) if ids else 0,'per_item':items};(OUT/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
