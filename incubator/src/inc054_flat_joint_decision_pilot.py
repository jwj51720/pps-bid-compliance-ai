#!/usr/bin/env python3
"""Repeated flat 24-label, full-notice diagnostic; no evidence policy."""
from __future__ import annotations
import argparse, csv, hashlib, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import inc001_simple_joint24 as common
import inc018_global_context_architecture as context

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'incubator/runs/inc054_flat_joint_decision_pilot'

def load():
 d=ROOT/'data/raw/open'; records={r['id']:r for r in common.read_jsonl_gz(d/'dev.jsonl.gz')}; labels={r['id']:r for r in common.read_csv(d/'dev_labels.csv')}; table=json.loads((d/'data/항목표.json').read_text(encoding='utf-8'))['항목']; return records,labels,table
def cohort(records,labels):
 chosen=set()
 for item in common.ITEMS:
  positives=[rid for rid in records if labels[rid][item]=='1']
  chosen.add(min(positives,key=lambda rid:hashlib.sha256(f'inc054:{item}:{rid}'.encode()).hexdigest()))
 remaining=sorted((rid for rid in records if rid not in chosen),key=lambda rid:hashlib.sha256(f'inc054:{rid}'.encode()).hexdigest()); chosen.update(remaining[:48-len(chosen)]); return sorted(chosen)
def schema(): return {'type':'object','additionalProperties':False,'required':list(common.ITEMS),'properties':{i:{'type':'integer','enum':[0,1]} for i in common.ITEMS}}
def messages(record,table):
 system='\n'.join(['당신은 공공입찰 공고의 법령 위반을 독립적으로 판정한다. 메타와 모든 원문 문서를 읽어 각 항목을 0 또는 1로 판단한다. 근거 문구를 출력하지 말고, 키워드만으로 단정하지 말며 불확실하면 0으로 둔다. JSON 객체 하나만 출력한다.',*[f'- {i}: {table[i]["항목명"]}' for i in common.ITEMS]])
 user='\n\n'.join(['[공고 ID]\n'+record['id'],'[메타]\n'+json.dumps(record['meta'],ensure_ascii=False,sort_keys=True),'[전체 문서]\n'+context.full_context(record)])
 return [{'role':'system','content':system},{'role':'user','content':user}]
def cfg(): return {'model':'google/gemma-4-26b-a4b-it','api_url':'https://openrouter.ai/api/v1/chat/completions','api_key_env':'OPENROUTER_API_KEY','temperature':0.0,'seed':20260905,'max_tokens':128,'timeout_seconds':120,'request_retries':1}
def run_one(rid,repeat,records,table):
 p=OUT/'records'/f'{rid}_{repeat}.json'
 if p.exists():return
 response:Any=None
 try:
  response=common.completion(cfg(),messages(records[rid],table),schema()); payload=common.parse_json(response.content)
  if set(payload)!=set(common.ITEMS) or any(payload[i] not in(0,1) for i in common.ITEMS):raise ValueError('invalid flat labels')
  entry={'id':rid,'repeat':repeat,'success':True,'usage':response.usage,'raw_response':response.content,'prediction':{i:int(payload[i]) for i in common.ITEMS}}
 except Exception as e: entry={'id':rid,'repeat':repeat,'success':False,'error':f'{type(e).__name__}: {e}','usage':{} if response is None else response.usage,'raw_response':'' if response is None else response.content}
 p.parent.mkdir(parents=True,exist_ok=True); common.write_json(p,entry)
def score(pred,labels,ids):
 out=[]
 for i in common.ITEMS:
  tp=fp=fn=0
  for rid in ids:
   g=int(labels[rid][i]);v=int(pred[rid][i]);tp+=g and v;fp+=not g and v;fn+=g and not v
  out.append({'item':i,'tp':tp,'fp':fp,'fn':fn,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0})
 return sum(x['f1'] for x in out)/24,out
def preflight():
 records,labels,table=load();ids=cohort(records,labels); man=[]
 for rid in ids:
  m=messages(records[rid],table)
  man.append({'id':rid,'prompt_sha256':common.sha256_text(json.dumps(m,ensure_ascii=False,sort_keys=True)),'message_characters':sum(len(x['content']) for x in m)})
 OUT.mkdir(parents=True,exist_ok=True);common.write_jsonl(OUT/'cohort.jsonl',man);common.write_json(OUT/'config.json',{'cohort_size':len(ids),'repeats':2,'model':cfg(),'max_calls':len(ids)*2,'max_cost_usd':.40});print(json.dumps({'status':'preflight_ok','cohort_size':len(ids),'calls':len(ids)*2,'max_message_characters':max(x['message_characters'] for x in man)},ensure_ascii=False,indent=2))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',required=True,choices=('preflight','run','aggregate'));ap.add_argument('--workers',type=int,default=16);a=ap.parse_args();load_dotenv(ROOT/'.env');OUT.mkdir(parents=True,exist_ok=True)
 if a.mode=='preflight':preflight();return
 records,labels,table=load();ids=cohort(records,labels)
 if a.mode=='run':
  with ThreadPoolExecutor(max_workers=a.workers) as ex:
   fs=[ex.submit(run_one,rid,rep,records,table) for rep in ('r1','r2') for rid in ids]
   for n,f in enumerate(as_completed(fs),1):f.result();print(f'completed={n}/{len(fs)}',flush=True)
  return
 baseline={r['id']:r for r in csv.DictReader((ROOT/'incubator/runs/inc041_v2_v3_v21_rule_composition_audit/dev_composed_predictions.csv').open(encoding='utf-8'))};report={'experiment_id':'inc054_flat_joint_decision_pilot','cohort_size':len(ids),'arms':{}}
 base_pred={rid:{i:int(baseline[rid][i]) for i in common.ITEMS} for rid in ids};bscore,bitems=score(base_pred,labels,ids);report['reference_inc041']={'macro_f1':bscore,'per_item':bitems}
 for rep in ('r1','r2'):
  entries=[json.loads((OUT/'records'/f'{rid}_{rep}.json').read_text()) for rid in ids];fail=[x for x in entries if not x['success']];row={'success':len(entries)-len(fail),'failures':len(fail),'cost':sum(float(x.get('usage',{}).get('cost',0)or 0) for x in entries)}
  if not fail: row['macro_f1'],row['per_item']=score({x['id']:x['prediction'] for x in entries},labels,ids);row['delta_vs_inc041']=row['macro_f1']-bscore
  report['arms'][rep]=row
 common.write_json(OUT/'metrics.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
