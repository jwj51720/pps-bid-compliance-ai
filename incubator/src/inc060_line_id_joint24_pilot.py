#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import inc001_simple_joint24 as common
import inc054_flat_joint_decision_pilot as base
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'incubator/runs/inc060_line_id_joint24_pilot';ABS={'v10','v11','v16','v18','v20'}
def lines(r):
 out=[]
 for d in sorted(r['docs'],key=lambda x:(common.DOCUMENT_ORDER[x['type']],x['doc_id'])):
  for x in d['text'].splitlines():
   if x:out.append(x)
 return out
def schema(r):
 n=len(lines(r));p={i:{'type':'integer','enum':[0,1]} for i in common.ITEMS};p.update({f'e{i[1:]}':{'type':'integer','enum':[-1,*range(n)]} for i in common.ITEMS if i not in ABS});return {'type':'object','additionalProperties':False,'required':list(p),'properties':p}
def messages(r,t):
 ls=lines(r);docs='\n'.join(f'[L{i}] {x}' for i,x in enumerate(ls));sys='\n'.join(['공공입찰 법령 위반을 판정한다. 메타와 전체 원문을 읽는다. 각 v는 0/1이다. non-absence v가 1이면 대응 e에 그 근거가 있는 L번호를, 0이면 -1을 출력한다. 부재탐지 항목은 e가 없다. 키워드만으로 단정하지 말고 불확실하면 0. JSON 하나만 출력.',*[f'- {i}: {t[i]["항목명"]}' for i in common.ITEMS]]);return [{'role':'system','content':sys},{'role':'user','content':'[메타]\n'+json.dumps(r['meta'],ensure_ascii=False,sort_keys=True)+'\n[원문 줄]\n'+docs}]
def one(rid,rep,rs,t):
 p=OUT/'records'/f'{rid}_{rep}.json'
 if p.exists():return
 resp:Any=None
 try:
  resp=common.completion({**base.cfg(),'max_tokens':512},messages(rs[rid],t),schema(rs[rid]));x=common.parse_json(resp.content);ls=lines(rs[rid]);pred={};ok=True
  for i in common.ITEMS:
   v=x.get(i);e=x.get(f'e{i[1:]}')
   if v not in(0,1):ok=False;break
   if i in ABS:pred[i]=int(v)
   elif (not v and e==-1) or (v and isinstance(e,int) and 0<=e<len(ls) and len(ls[e])<=500):pred[i]=int(v)
   else:ok=False;break
  if not ok:raise ValueError('invalid line-id response')
  z={'id':rid,'repeat':rep,'success':True,'usage':resp.usage,'prediction':pred,'raw_response':resp.content}
 except Exception as e:z={'id':rid,'repeat':rep,'success':False,'error':f'{type(e).__name__}: {e}','usage':{} if resp is None else resp.usage,'raw_response':'' if resp is None else resp.content}
 p.parent.mkdir(parents=True,exist_ok=True);common.write_json(p,z)
def main():
 a=argparse.ArgumentParser();a.add_argument('--mode',required=True,choices=('preflight','run','aggregate'));a.add_argument('--workers',type=int,default=16);q=a.parse_args();load_dotenv(ROOT/'.env');rs,lab,t=base.load();ids=base.cohort(rs,lab)
 if q.mode=='preflight':
  m=[{'id':i,'line_count':len(lines(rs[i])),'chars':sum(len(x['content']) for x in messages(rs[i],t))} for i in ids];OUT.mkdir(parents=True,exist_ok=True);common.write_jsonl(OUT/'cohort.jsonl',m);print(json.dumps({'cohort':len(ids),'calls':len(ids)*2,'max_lines':max(x['line_count'] for x in m),'max_chars':max(x['chars'] for x in m)},ensure_ascii=False));return
 if q.mode=='run':
  with ThreadPoolExecutor(max_workers=q.workers) as ex:
   fs=[ex.submit(one,i,r,rs,t) for r in ('r1','r2') for i in ids]
   for n,f in enumerate(as_completed(fs),1):f.result();print(f'{n}/{len(fs)}',flush=True)
  return
 report={'experiment_id':'inc060_line_id_joint24_pilot','arms':{}}
 for rep in ('r1','r2'):
  es=[json.loads((OUT/'records'/f'{i}_{rep}.json').read_text()) for i in ids];bad=[x for x in es if not x['success']];report['arms'][rep]={'success':len(es)-len(bad),'failures':len(bad),'cost':sum(float(x.get('usage',{}).get('cost',0)or 0) for x in es)}
  if not bad:report['arms'][rep]['macro_f1'],report['arms'][rep]['per_item']=base.score({x['id']:x['prediction'] for x in es},lab,ids)
 common.write_json(OUT/'metrics.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
