#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import inc001_simple_joint24 as common
import inc018_global_context_architecture as ctx
import inc054_flat_joint_decision_pilot as cohort
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'incubator/runs/inc063_joint_consensus_pilot'
def load():return cohort.load()
def msgs(r,t):return ctx.build_messages(r,common.build_system_prompt(t),ctx.full_context(r))
def cfg():return {'model':'google/gemma-4-26b-a4b-it','api_url':'https://openrouter.ai/api/v1/chat/completions','api_key_env':'OPENROUTER_API_KEY','temperature':0.,'seed':20260905,'max_tokens':1800,'timeout_seconds':120,'request_retries':1}
def one(i,k,rs,t):
 p=OUT/'records'/f'{i}_{k}.json'
 if p.exists():return
 o:Any=None
 try:
  o=common.completion(cfg(),msgs(rs[i],t),common.judgment_schema());j,w=common.postprocess(common.parse_json(o.content),rs[i]);z={'id':i,'run':k,'success':True,'judgment':j,'usage':o.usage,'raw':o.content,'warnings':w}
 except Exception as e:z={'id':i,'run':k,'success':False,'error':f'{type(e).__name__}: {e}','usage':{} if o is None else o.usage,'raw':'' if o is None else o.content}
 p.parent.mkdir(parents=True,exist_ok=True);common.write_json(p,z)
def score(rows,lab,ids):
 vals=[]
 for it in common.ITEMS:
  tp=fp=fn=0
  for r in rows:
   g=int(lab[r['id']][it]);p=int(r[it]);tp+=g and p;fp+=not g and p;fn+=g and not p
  vals.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0)
 return sum(vals)/24
def main():
 a=argparse.ArgumentParser();a.add_argument('--mode',required=True,choices=('preflight','run','aggregate'));a.add_argument('--workers',type=int,default=16);q=a.parse_args();load_dotenv(ROOT/'.env');rs,lab,t=load();ids=cohort.cohort(rs,lab);OUT.mkdir(parents=True,exist_ok=True)
 if q.mode=='preflight':
  common.write_jsonl(OUT/'cohort.jsonl',[{'id':i,'prompt_sha256':common.sha256_text(json.dumps(msgs(rs[i],t),ensure_ascii=False,sort_keys=True))} for i in ids]);print(json.dumps({'cohort':len(ids),'calls':len(ids)*3,'max_cost_usd':.5},ensure_ascii=False));return
 if q.mode=='run':
  with ThreadPoolExecutor(max_workers=q.workers) as ex:
   fs=[ex.submit(one,i,k,rs,t) for k in ('r1','r2','r3') for i in ids]
   for n,f in enumerate(as_completed(fs),1):f.result();print(f'{n}/{len(fs)}',flush=True)
  return
 report={'experiment_id':'inc063_joint_consensus_pilot','raw':{},'consensus':{}}
 allruns={}
 for k in ('r1','r2','r3'):
  es=[json.loads((OUT/'records'/f'{i}_{k}.json').read_text()) for i in ids];bad=[x for x in es if not x['success']];report['raw'][k]={'success':len(es)-len(bad),'failures':len(bad),'cost':sum(float(x.get('usage',{}).get('cost',0)or 0)for x in es)}
  if not bad:
   rows=[]
   for x in es: rows.append(common.to_row(x['id'],x['judgment']))
   report['raw'][k]['macro_f1']=score(rows,lab,ids);allruns[k]=es
 if len(allruns)==3:
  rows=[];valid=True
  for i in ids:
   j={}
   for it in common.ITEMS:
    cells=[allruns[k][ids.index(i)]['judgment'][it] for k in ('r1','r2','r3')];p=sum(c['위반여부'] for c in cells)>=2
    ev=next((c['근거문구'] for c in cells if p and c['위반여부'] and c['근거문구']), '')
    if p and it not in common.ABSENCE_ITEMS and not ev:valid=False
    j[it]={'위반여부':int(p),'근거문구':ev if p else ''}
   rows.append(common.to_row(i,j))
  report['consensus']={'evidence_valid':valid,'macro_f1':score(rows,lab,ids),'mean_raw_macro_f1':sum(report['raw'][k]['macro_f1'] for k in allruns)/3}
 common.write_json(OUT/'metrics.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
