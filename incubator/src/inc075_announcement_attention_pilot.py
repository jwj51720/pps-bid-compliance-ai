#!/usr/bin/env python3
"""INC-075: full notice versus announcement-only attention for v7/v23."""
from __future__ import annotations
import argparse, hashlib, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import inc001_simple_joint24 as common
import inc018_global_context_architecture as context

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'incubator/runs/inc075_announcement_attention_pilot';ITEMS=('v7','v23')
def load():
 d=ROOT/'data/raw/open';rs={x['id']:x for x in common.read_jsonl_gz(d/'dev.jsonl.gz')};ls={x['id']:x for x in common.read_csv(d/'dev_labels.csv')};table=json.loads((d/'data/항목표.json').read_text())['항목'];return rs,ls,table
def cohort(rs,ls):
 s=set()
 for x in ITEMS:s.add(min((rid for rid in rs if ls[rid][x]=='1'),key=lambda rid:hashlib.sha256(f'inc075:{x}:{rid}'.encode()).hexdigest()))
 rem=sorted((rid for rid in rs if rid not in s),key=lambda rid:hashlib.sha256(f'inc075:r:{rid}'.encode()).hexdigest());s.update(rem[:24-len(s)]);return sorted(s)
def schema():return {'type':'object','additionalProperties':False,'required':list(ITEMS),'properties':{x:{'type':'object','additionalProperties':False,'required':['v','e'],'properties':{'v':{'type':'integer','enum':[0,1]},'e':{'type':['string','null'],'maxLength':500}}} for x in ITEMS}}
def messages(r,table,arm):
 sys='\n'.join(['당신은 공공입찰 공고의 법령 위반을 판단한다. 키워드만으로 단정하지 말고 적용 전제·실제 제한·예외를 확인한다.','v=1이면 e는 원문의 변경 없는 연속 부분문자열 500자 이하여야 하고, 0이면 null이다.','판정 항목:',*(f'- {x}: {table[x]["항목명"]}' for x in ITEMS),'JSON 하나만 출력한다.'])
 if arm=='full':docs=context.full_context(r)
 else:
  selected=[d for d in r['docs'] if d['type']=='공고문'];docs='\n\n'.join(f'[{d["type"]}:{d["doc_id"]}]\n{d["text"]}' for d in selected)
  if not selected:docs='[공고문 없음]'
 return [{'role':'system','content':sys},{'role':'user','content':'[메타]\n'+json.dumps(r['meta'],ensure_ascii=False,sort_keys=True)+'\n\n[문서]\n'+docs}]
def cfg():return {'model':'google/gemma-4-26b-a4b-it','api_url':'https://openrouter.ai/api/v1/chat/completions','api_key_env':'OPENROUTER_API_KEY','temperature':0.0,'seed':20260905,'max_tokens':400,'timeout_seconds':120,'request_retries':1}
def validate(p,r):
 src='\n'.join(d['text'] for d in r['docs']);out={}
 for x in ITEMS:
  c=p.get(x)
  if not isinstance(c,dict) or c.get('v')not in(0,1):raise ValueError(x)
  v=int(c['v']);e=c.get('e');e=e.strip() if isinstance(e,str) else ''
  if v and e not in src:v,e=0,''
  elif not v:e=''
  out[x]={'v':v,'e':e}
 return out
def one(rid,arm,rep,rs,table):
 p=OUT/'records'/f'{rid}_{arm}_{rep}.json'
 if p.exists():return
 response:Any=None
 try:
  response=common.completion(cfg(),messages(rs[rid],table,arm),schema());entry={'id':rid,'arm':arm,'repeat':rep,'success':True,'usage':response.usage,'raw_response':response.content,'prediction':validate(common.parse_json(response.content),rs[rid])}
 except Exception as e:entry={'id':rid,'arm':arm,'repeat':rep,'success':False,'error':f'{type(e).__name__}: {e}','usage':{} if response is None else response.usage,'raw_response':'' if response is None else response.content}
 p.parent.mkdir(parents=True,exist_ok=True);common.write_json(p,entry)
def score(p,ls,ids):
 rows=[]
 for x in ITEMS:
  tp=fp=fn=0
  for rid in ids:
   g=int(ls[rid][x]);v=p[rid][x]['v'];tp+=g and v;fp+=not g and v;fn+=g and not v
  rows.append({'item':x,'tp':tp,'fp':fp,'fn':fn,'f1':2*tp/(2*tp+fp+fn)if 2*tp+fp+fn else 0})
 return {'macro_f1':sum(x['f1']for x in rows)/2,'per_item':rows}
def preflight():
 rs,ls,t=load();ids=cohort(rs,ls);man=[]
 for rid in ids:man.append({'id':rid,'positive':[x for x in ITEMS if ls[rid][x]=='1'],'full_sha':common.sha256_text(json.dumps(messages(rs[rid],t,'full'),ensure_ascii=False,sort_keys=True)),'announcement_sha':common.sha256_text(json.dumps(messages(rs[rid],t,'announcement'),ensure_ascii=False,sort_keys=True))})
 OUT.mkdir(parents=True,exist_ok=True);common.write_jsonl(OUT/'cohort.jsonl',man);common.write_json(OUT/'config.json',{'items':ITEMS,'cohort':len(ids),'calls':len(ids)*4,'max_cost_usd':.30,'promotion':'both announcement-full deltas positive; no target recall loss; source evidence valid'});print(json.dumps({'status':'preflight_ok','cohort':len(ids),'calls':len(ids)*4},ensure_ascii=False))
def run(workers):
 rs,ls,t=load();ids=cohort(rs,ls);jobs=[(rid,a,rep)for rid in ids for a in('full','announcement')for rep in('r1','r2')]
 with ThreadPoolExecutor(max_workers=workers)as ex:
  fs=[ex.submit(one,*j,rs,t)for j in jobs]
  for n,f in enumerate(as_completed(fs),1):f.result();print(f'completed={n}/{len(fs)}',flush=True)
def aggregate():
 rs,ls,t=load();ids=cohort(rs,ls);report={'experiment_id':'inc075_announcement_attention_pilot','cohort':len(ids),'repeats':{}}
 for rep in('r1','r2'):
  a={}
  for arm in('full','announcement'):
   es=[json.loads((OUT/'records'/f'{rid}_{arm}_{rep}.json').read_text())for rid in ids];a[arm]={'success':sum(x['success']for x in es),'failures':sum(not x['success']for x in es),'cost_usd':sum(float(x.get('usage',{}).get('cost',0)or 0)for x in es)}
   if not a[arm]['failures']:a[arm].update(score({x['id']:x['prediction']for x in es},ls,ids))
  if not a['full']['failures']and not a['announcement']['failures']:a['delta']=a['announcement']['macro_f1']-a['full']['macro_f1']
  report['repeats'][rep]=a
 common.write_json(OUT/'metrics.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',required=True,choices=('preflight','run','aggregate'));p.add_argument('--workers',type=int,default=16);a=p.parse_args();load_dotenv(ROOT/'.env');OUT.mkdir(parents=True,exist_ok=True);{'preflight':preflight,'run':lambda:run(a.workers),'aggregate':aggregate}[a.mode]()
if __name__=='__main__':main()
