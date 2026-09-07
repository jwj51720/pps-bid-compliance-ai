#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import inc001_simple_joint24 as common
import inc054_flat_joint_decision_pilot as cohort_base
import inc060_line_id_joint24_pilot as line_base
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'incubator/runs/inc062_per_positive_evidence_locator';ABS={'v10','v11','v16','v18','v20'}
def load():
 rs,lab,t=cohort_base.load();ids=cohort_base.cohort(rs,lab);p={r['id']:r for r in csv.DictReader((ROOT/'incubator/runs/inc041_v2_v3_v21_rule_composition_audit/dev_composed_predictions.csv').open(encoding='utf-8'))};jobs=[(i,v) for i in ids for v in common.ITEMS if v not in ABS and int(p[i][v])];return rs,t,jobs
def msg(r,t,v):
 ls=line_base.lines(r);return [{'role':'system','content':f'공공입찰 공고의 {v} ({t[v]["항목명"]}) 위반 판단이 이미 양성으로 고정되었다. 전체 원문에서 그 판단을 지지하는 변경 없는 원문 줄 하나를 고른다. 확신이 없으면 -1. JSON 하나만 출력.'},{'role':'user','content':'[메타]\n'+json.dumps(r['meta'],ensure_ascii=False,sort_keys=True)+'\n[원문 줄]\n'+'\n'.join(f'[L{i}] {x}' for i,x in enumerate(ls))}]
def one(i,v,rs,t):
 p=OUT/'records'/f'{i}_{v}.json'
 if p.exists():return
 resp:Any=None
 try:
  ls=line_base.lines(rs[i]);schema={'type':'object','additionalProperties':False,'required':['line_id'],'properties':{'line_id':{'type':'integer','enum':[-1,*range(len(ls))]}}};resp=common.completion({**cohort_base.cfg(),'max_tokens':128},msg(rs[i],t,v),schema);x=common.parse_json(resp.content);n=x.get('line_id');ok=isinstance(n,int) and (n==-1 or 0<=n<len(ls)) and (n==-1 or len(ls[n])<=500);z={'id':i,'item':v,'success':ok,'line_id':n if ok else -1,'usage':resp.usage,'raw_response':resp.content}
 except Exception as e:z={'id':i,'item':v,'success':False,'error':f'{type(e).__name__}: {e}','line_id':-1,'usage':{} if resp is None else resp.usage,'raw_response':'' if resp is None else resp.content}
 p.parent.mkdir(parents=True,exist_ok=True);common.write_json(p,z)
def main():
 a=argparse.ArgumentParser();a.add_argument('--mode',required=True,choices=('preflight','run','aggregate'));a.add_argument('--workers',type=int,default=16);q=a.parse_args();load_dotenv(ROOT/'.env');rs,t,jobs=load();OUT.mkdir(parents=True,exist_ok=True)
 if q.mode=='preflight':common.write_jsonl(OUT/'jobs.jsonl',[{'id':i,'item':v,'prompt_sha256':common.sha256_text(json.dumps(msg(rs[i],t,v),ensure_ascii=False,sort_keys=True))} for i,v in jobs]);print(json.dumps({'jobs':len(jobs),'max_cost_usd':.25},ensure_ascii=False));return
 if q.mode=='run':
  with ThreadPoolExecutor(max_workers=q.workers) as ex:
   fs=[ex.submit(one,i,v,rs,t) for i,v in jobs]
   for n,f in enumerate(as_completed(fs),1):f.result();print(f'{n}/{len(fs)}',flush=True)
  return
 es=[json.loads((OUT/'records'/f'{i}_{v}.json').read_text()) for i,v in jobs];report={'experiment_id':'inc062_per_positive_evidence_locator','jobs':len(es),'transport_success':sum(x['success'] for x in es),'valid_nonnegative_id':sum(x['success'] and x['line_id']>=0 for x in es),'negative_one':sum(x['success'] and x['line_id']==-1 for x in es),'cost':sum(float(x.get('usage',{}).get('cost',0)or 0) for x in es)};common.write_json(OUT/'report.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
