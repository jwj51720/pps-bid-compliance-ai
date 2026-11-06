#!/usr/bin/env python3
"""INC-068 paired same-conversation self-deliberation pilot."""
from __future__ import annotations
import argparse, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import inc001_simple_joint24 as common
import inc018_global_context_architecture as context
import inc066_attention_proposal_topology_pilot as base

ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'incubator/runs/inc068_self_deliberation_pilot'
def cfg(n:int): return base.config(n)
def memo_schema(): return {'type':'object','additionalProperties':False,'required':['memo'],'properties':{'memo':{'type':'string','minLength':1}}}
def init(r,t):
 s='\n'.join(['공공입찰 공고의 법령 위반을 독립적으로 검토한다. 메타와 모든 원문을 읽고 적용 조건과 예외를 고려한다.',*[f'- {i}: {t[i]["항목명"]}' for i in common.ITEMS]])
 u='\n\n'.join(['[메타]\n'+json.dumps(r['meta'],ensure_ascii=False,sort_keys=True),'[전체 문서]\n'+context.full_context(r)])
 return [{'role':'system','content':s},{'role':'user','content':u}]
def valid(x):
 if set(x)!=set(common.ITEMS) or any(x[i] not in(0,1) for i in common.ITEMS): raise ValueError('labels')
 return {i:int(x[i]) for i in common.ITEMS}
def one(kind,rid,rep,rs,t):
 p=OUT/kind/f'{rid}_{rep}.json'
 if p.exists(): return
 a=b=None
 try:
  m=init(rs[rid],t)
  if kind=='control':
   m[0]['content']+='\n최종 0/1만 JSON 객체 하나로 출력한다. 불확실하면 0.'; a=common.completion(cfg(256),m,base.label_schema()); z={'id':rid,'success':True,'prediction':valid(common.parse_json(a.content)),'usage':a.usage}
  else:
   m[0]['content']+='\nv1부터 v24까지 한 줄씩 잠정 0/1과 법률상 이유를 간결히 적는다. 인용문과 줄번호는 쓰지 않는다. JSON 객체 하나만 출력한다.';a=common.completion(cfg(1024),m,memo_schema());memo=common.parse_json(a.content).get('memo')
   if not isinstance(memo,str) or any(f'v{i}' not in memo for i in range(1,25)): raise ValueError('memo coverage')
   f=init(rs[rid],t)+[{'role':'assistant','content':memo},{'role':'user','content':'위 잠정 메모는 오류 가능성이 있으며 증거나 라벨 조건이 아니다. 전체 원문과 메타를 다시 우선해 독립적으로 재검토하고 최종 0/1만 JSON 객체 하나로 출력하라.'}];b=common.completion(cfg(256),f,base.label_schema());z={'id':rid,'success':True,'prediction':valid(common.parse_json(b.content)),'memo':memo,'memo_usage':a.usage,'usage':b.usage}
 except Exception as e:z={'id':rid,'success':False,'error':f'{type(e).__name__}: {e}','memo_usage':{} if a is None or kind=='control' else a.usage,'usage':{} if b is None else b.usage}
 p.parent.mkdir(parents=True,exist_ok=True);common.write_json(p,z)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',required=True,choices=('preflight','run','aggregate'));ap.add_argument('--workers',type=int,default=16);q=ap.parse_args();load_dotenv(ROOT/'.env');rs,lab,t=base.load();ids=base.seed_cohort(rs,lab);OUT.mkdir(parents=True,exist_ok=True)
 if q.mode=='preflight':
  common.write_json(OUT/'config.json',{'cohort':ids,'calls':len(ids)*6,'max_cost_usd':.5,'protocol':'incubator/docs/inc068_self_deliberation_protocol.md'});print(json.dumps({'status':'preflight_ok','cohort':len(ids),'calls':len(ids)*6},ensure_ascii=False));return
 if q.mode=='run':
  jobs=[(k,i,r) for r in ('r1','r2') for k in ('control','treatment') for i in ids]
  with ThreadPoolExecutor(max_workers=q.workers) as ex:
   fs=[ex.submit(one,k,i,r,rs,t) for k,i,r in jobs]
   for n,f in enumerate(as_completed(fs),1):f.result();print(f'{n}/{len(fs)}',flush=True)
  return
 rep={'experiment_id':'inc068_self_deliberation_pilot','repeats':{}};cost=0
 for r in ('r1','r2'):
  c=[json.loads((OUT/'control'/f'{i}_{r}.json').read_text()) for i in ids];z=[json.loads((OUT/'treatment'/f'{i}_{r}.json').read_text()) for i in ids];cf=[x for x in c if not x['success']];tf=[x for x in z if not x['success']];cost+=sum(float(x.get('usage',{}).get('cost',0)or 0)+float(x.get('memo_usage',{}).get('cost',0)or 0) for x in c+z);row={'control_success':len(c)-len(cf),'treatment_success':len(z)-len(tf),'control_failures':cf,'treatment_failures':tf}
  if not cf and not tf:
   cm,ci,*_=base.score({x['id']:x['prediction'] for x in c},lab,ids);tm,ti,*_=base.score({x['id']:x['prediction'] for x in z},lab,ids);row.update({'control_macro_f1':cm,'treatment_macro_f1':tm,'delta':tm-cm,'control_per_item':ci,'treatment_per_item':ti})
  rep['repeats'][r]=row
 rep['reported_cost_usd']=cost;common.write_json(OUT/'report.json',rep);print(json.dumps(rep,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
