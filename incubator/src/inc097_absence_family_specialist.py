#!/usr/bin/env python3
"""Independent full-context teacher for the five organizer-defined absence items."""
from __future__ import annotations
import argparse,concurrent.futures,csv,gzip,json,os,time
from pathlib import Path
import requests
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[2]; DATA=ROOT/'data/raw/open'; CARDS=ROOT/'incubator/reference/dev_history/decision_cards_v6.json';OUT=ROOT/'incubator/runs/inc097_absence_family_specialist_dev200'; ITEMS=('v10','v11','v16','v18','v20')
def gz(p):
 with gzip.open(p,'rt',encoding='utf8') as h:return [json.loads(x) for x in h if x]
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf8').splitlines() if x]
def schema():return {'type':'object','additionalProperties':False,'required':list(ITEMS),'properties':{i:{'type':'integer','enum':[0,1]} for i in ITEMS}}
def docs(r):return '\n\n'.join(f'[{d["type"]}|{d["doc_id"]}]\n{d["text"]}' for d in r['docs'])
def msg(r,c):
 legal='\n\n'.join(f'[{i}|{c[i]["item_name"]}]\n{c[i]["prompt_text"]}' for i in ITEMS)
 sys='''당신은 공공입찰의 부재형 법령위반만 판정하는 독립 검토자다. 이 호출은 v10,v11,v16,v18,v20만 다룬다. 각 항목에서 반드시 (A) metadata·원문의 적용대상 사실, (B) 모든 문서에서 필요한 제한/확인/예외의 존재, (C) 카드의 예외를 분리해 검토한다. A가 확인되고 B가 공고 전체에 없을 때만 1이다. 다른 항목의 제한이나 일반적인 문구를 B의 존재로 오인하지 않는다. metadata의 조항호내용·세부품명번호·업무구분·예산은 적용성을 판단하는 제공 사실이며, 원문과 함께 사용한다. 최종 5개 0/1 JSON만 출력한다.'''
 u='[부재형 법령판단 카드]\n'+legal+'\n\n[metadata]\n'+json.dumps(r['meta'],ensure_ascii=False,sort_keys=True)+'\n\n[공고 원문 전체]\n'+docs(r)
 return [{'role':'system','content':sys},{'role':'user','content':u}]
def call(k,m):
 p={'model':'gpt-5.6-luna','input':m,'max_output_tokens':8192,'store':False,'reasoning':{'effort':'high'},'text':{'format':{'type':'json_schema','name':'inc097_absence','strict':True,'schema':schema()}}}
 for a in range(4):
  try:
   q=requests.post('https://api.openai.com/v1/responses',headers={'Authorization':f'Bearer {k}','Content-Type':'application/json'},json=p,timeout=300);b=q.json();t=b.get('output_text') or ''.join(z.get('text','') for x in b.get('output',[]) if x.get('type')=='message' for z in x.get('content',[]) if z.get('type')=='output_text')
   if q.ok and t:
    v=json.loads(t)
    if set(v)==set(ITEMS) and all(v[i] in(0,1) for i in ITEMS):return {'success':True,'labels':v,'usage':b.get('usage',{}),'raw_response':t}
   err=f'{q.status_code}:{str(b)[:300]}'
  except Exception as e:err=f'{type(e).__name__}:{e}'
  time.sleep(2**a)
 return {'success':False,'error':err}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=('run','score'),default='run');ap.add_argument('--workers',type=int,default=16);a=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True);rs=gz(DATA/'dev.jsonl.gz');cards=json.loads(CARDS.read_text(encoding='utf8'))['cards']
 if a.mode=='run':
  load_dotenv(ROOT/'.env');k=os.getenv('OPENAI_API_KEY');assert k;ck=OUT/'checkpoint.jsonl';done={x['id']:x for x in jl(ck)} if ck.exists() else {};pending=[r for r in rs if not done.get(r['id'],{}).get('success')]
  with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
   fs={ex.submit(call,k,msg(r,cards)):r['id'] for r in pending}
   for n,f in enumerate(concurrent.futures.as_completed(fs),1):x=f.result();x['id']=fs[f];open(ck,'a',encoding='utf8').write(json.dumps(x,ensure_ascii=False)+'\n');print(n,len(fs),x['id'],x['success'],flush=True)
 else:
  gold={x['id']:x for x in csv.DictReader((DATA/'dev_labels.csv').open(encoding='utf8'))};d={x['id']:x for x in jl(OUT/'checkpoint.jsonl') if x.get('success')};out={}
  for i in ITEMS:
   tp=fp=fn=0
   for rid,x in d.items():y=int(gold[rid][i]);v=x['labels'][i];tp+=v==y==1;fp+=v==1 and y==0;fn+=v==0 and y==1
   out[i]={'tp':tp,'fp':fp,'fn':fn,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0}
  print(json.dumps({'success':len(d),'per_item':out,'macro':sum(x['f1'] for x in out.values())/5},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
