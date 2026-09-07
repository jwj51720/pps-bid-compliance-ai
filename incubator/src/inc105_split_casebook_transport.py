#!/usr/bin/env python3
from __future__ import annotations
import argparse,concurrent.futures,gzip,json,os
from pathlib import Path
from typing import Any
import requests
from dotenv import load_dotenv
import inc001_simple_joint24 as common
import inc081_teacher_full_context_calibration as calibration
from evidence_resolver import resolve_quote

ROOT=Path(__file__).resolve().parents[2];RAW=ROOT/'data/raw/open';CARDS=ROOT/'incubator/reference/dev_history/decision_cards_v6.json';MANI=ROOT/'incubator/runs/inc080_teacher_pilot_manifest/manifest.jsonl';OUT=ROOT/'incubator/runs/inc105_split_casebook_transport';ITEMS=common.ITEMS
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf8').splitlines() if x]
def successful_by_id(path):
 if not path.exists():return {}
 return {x['id']:x for x in jl(path) if x.get('success')}
def send(key,msg,cap,effort,schema,name):
 p={'model':'gpt-5.6-luna','input':msg,'max_output_tokens':cap,'store':False,'reasoning':{'effort':effort},'text':{'format':{'type':'json_schema','name':name,'strict':True,'schema':schema}}}
 try:
  q=requests.post('https://api.openai.com/v1/responses',headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},json=p,timeout=360);b=q.json();t=b.get('output_text') or ''.join(z.get('text','') for x in b.get('output',[]) if x.get('type')=='message' for z in x.get('content',[]) if z.get('type')=='output_text')
  return {'success':bool(q.ok and t),'value':json.loads(t) if q.ok and t else None,'error':'' if q.ok and t else f'{q.status_code}:{b.get("status")}:{b.get("incomplete_details")}', 'raw_response':t}
 except Exception as e:return {'success':False,'error':f'{type(e).__name__}:{e}','raw_response':''}
def core(c):return '\n\n'.join(f'[{i}|{x["item_name"]}]\n{x["prompt_text"]}' for i,x in c['cards'].items())
def m1(r,c):return [{'role':'system','content':'공공입찰 법령 위반을 판정한다. 원문·metadata·항목카드만 사용하고 각 항목을 적용대상, 사실, 예외 순서로 독립 판단한다. JSON만 출력한다.'},{'role':'user','content':'[카드]\n'+core(c)+'\n\n[metadata]\n'+json.dumps(r['meta'],ensure_ascii=False,sort_keys=True)+'\n\n[원문]\n'+calibration.render_documents(r)}]
def m2(r,c,pos):return [{'role':'system','content':'고정된 양성 항목마다 판단 근거를 원문에서 찾아 basis와 변경 없는 연속 substring quote를 기록한다. 판단·라벨을 변경하지 않는다. 근거가 없으면 두 필드를 빈 문자열로 둔다. JSON만 출력한다.'},{'role':'user','content':'[양성 항목]\n'+json.dumps(pos,ensure_ascii=False)+'\n\n[카드]\n'+core(c)+'\n\n[metadata]\n'+json.dumps(r['meta'],ensure_ascii=False,sort_keys=True)+'\n\n[원문]\n'+calibration.render_documents(r)}]
def evidence_schema(pos):
 e={'type':'object','additionalProperties':False,'required':['basis','quote'],'properties':{'basis':{'type':'string','maxLength':240},'quote':{'type':'string','maxLength':500}}}
 return {'type':'object','additionalProperties':False,'required':['evidence'],'properties':{'evidence':{'type':'object','additionalProperties':False,'required':pos,'properties':{i:e for i in pos}}}}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--start',type=int,default=16);ap.add_argument('--size',type=int,default=8);ap.add_argument('--run-id',default='inc105_split_casebook_transport');ap.add_argument('--stage-a-cap',type=int,default=4096);args=ap.parse_args()
 mani=jl(MANI)[args.start:args.start+args.size]
 with gzip.open(RAW/'train_unlabeled.jsonl.gz','rt',encoding='utf8') as h:rs={x['id']:x for x in (json.loads(y) for y in h if y)}
 c=json.loads(CARDS.read_text(encoding='utf8'));load_dotenv(ROOT/'.env');key=os.environ['OPENAI_API_KEY'];output=ROOT/'incubator/runs'/args.run_id;output.mkdir(parents=True,exist_ok=True)
 s1={'type':'object','additionalProperties':False,'required':['case_signature','labels'],'properties':{'case_signature':{'type':'string','maxLength':700},'labels':{'type':'object','additionalProperties':False,'required':list(ITEMS),'properties':{i:{'type':'integer','enum':[0,1]} for i in ITEMS}}}}
 a=successful_by_id(output/'stage_a.jsonl')
 pending_a=[x['id'] for x in mani if x['id'] not in a]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
  fs={ex.submit(send,key,m1(rs[rid],c),args.stage_a_cap,'high',s1,'inc105_labels'):rid for rid in pending_a}
  for n,f in enumerate(concurrent.futures.as_completed(fs),1):
   rid=fs[f];a[rid]=f.result();a[rid]['id']=rid;open(output/'stage_a.jsonl','a',encoding='utf8').write(json.dumps(a[rid],ensure_ascii=False)+'\n');print('A',n,len(fs),rid,a[rid]['success'],flush=True)
 b=successful_by_id(output/'stage_b.jsonl')
 pending_b=[rid for rid in a if a[rid]['success'] and rid not in b]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
  fs={ex.submit(send,key,m2(rs[rid],c,[i for i,v in a[rid]['value']['labels'].items() if v]),2048,'medium',evidence_schema([i for i,v in a[rid]['value']['labels'].items() if v]),'inc105_evidence'):rid for rid in pending_b}
  for n,f in enumerate(concurrent.futures.as_completed(fs),1):
   rid=fs[f];b[rid]=f.result();b[rid]['id']=rid;open(output/'stage_b.jsonl','a',encoding='utf8').write(json.dumps(b[rid],ensure_ascii=False)+'\n');print('B',n,len(fs),rid,b[rid]['success'],flush=True)
 rows=[]
 for rid,x in a.items():
  z={'id':rid,'stage_a':x,'stage_b':b.get(rid)}
  if x['success'] and b.get(rid,{}).get('success'):
   ev=b[rid]['value']['evidence'];resolved={}
   for i,v in x['value']['labels'].items():
    if v:resolved[i]=resolve_quote(ev[i]['quote'],rs[rid]['docs'])
   z['resolved']=resolved
  rows.append(z)
 (output/'records.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n',encoding='utf8')
 positives=sum(v for x in a.values() if x['success'] for v in x['value']['labels'].values());resolved=sum(bool(v) for x in rows for v in x.get('resolved',{}).values() if v[0]);report={'notices':len(mani),'stage_a_success':sum(x['success'] for x in a.values()),'stage_b_success':sum(x.get('success',False) for x in b.values()),'positives':positives,'resolved_positive_evidence':resolved};(output/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
