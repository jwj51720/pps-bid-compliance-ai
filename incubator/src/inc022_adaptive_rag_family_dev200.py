#!/usr/bin/env python3
"""INC-021 rerun with per-notice exact legal-context admission."""
from __future__ import annotations
import argparse,csv,fcntl,json
from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import Counter
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from transformers import AutoTokenizer
import inc001_simple_joint24 as common
import inc021_rag_family_pass_dev200 as base
from inc007_token_admission_profile import count_messages
from inc006_input_budget_ablation import metric

def readj(p:Path)->list[dict[str,Any]]:return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def append(p:Path,x:dict[str,Any])->None:
 with p.open('a',encoding='utf-8') as h:h.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n');h.flush()
def main()->None:
 a=argparse.ArgumentParser();a.add_argument('--config',default='incubator/configs/inc022_adaptive_rag_family_dev200.json');a.add_argument('--mode',choices=('preflight','run'),default='preflight');z=a.parse_args();root=common.repo_root();cfg=json.loads((root/z.config).read_text());load_dotenv(root/'.env');out=root/'incubator/runs'/cfg['experiment_id'];out.mkdir(parents=True,exist_ok=True);lock=(out/'.run.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 data=root/cfg['data_root'];records={r['id']:r for r in common.read_jsonl_gz(data/'dev.jsonl.gz')};labels={r['id']:r for r in common.read_csv(data/'dev_labels.csv')};table=json.loads((data/'data/항목표.json').read_text())['항목'];idx=json.loads((root/cfg['rag_index_path']).read_text());retrieval={r['item']:r for r in idx['retrieval']};tok=AutoTokenizer.from_pretrained(cfg['model_tokenizer']);budget=cfg['max_model_len']-cfg['output_reserve_tokens'];prepared=[]
 for r in records.values():
  for family,items in base.FAMILIES.items():
   lo,hi,best=0,cfg['law_excerpt_max_chars'],0
   while lo<=hi:
    mid=(lo+hi)//2;m=base.messages(r,items,base.card(family,items,table,retrieval,mid));n=count_messages(tok,m)
    if n<=budget:best=mid;lo=mid+1
    else:hi=mid-1
   if best==0:raise RuntimeError(f'fixed prompt overflow {r["id"]} {family}')
   m=base.messages(r,items,base.card(family,items,table,retrieval,best));n=count_messages(tok,m);prepared.append({'id':r['id'],'family':family,'items':items,'law_excerpt_chars':best,'messages':m,'prompt_tokens':n,'prompt_sha256':common.sha256_text(json.dumps(m,ensure_ascii=False,sort_keys=True))})
 estimate=sum(q['prompt_tokens']*cfg['observed_input_cost_per_token_usd']+cfg['assumed_completion_tokens']*cfg['observed_completion_cost_per_token_usd'] for q in prepared);dist=Counter(q['law_excerpt_chars'] for q in prepared);plan={'experiment_id':cfg['experiment_id'],'hypothesis':'per-notice exact admission of up to 600 legal-context characters restores RAG-family recall without losing its precision/evidence benefit','changed_variable':'legal excerpt length is maximized per notice/family under exact token admission; documents remain complete','cohort_count':len(records),'request_count':len(prepared),'law_excerpt_distribution':dict(sorted(dist.items())),'prompt_token_budget':budget,'prompt_token_max':max(q['prompt_tokens'] for q in prepared),'projected_cost_usd':estimate,'max_cost_usd':cfg['max_cost_usd'],'success_gate':'macro F1 > INC-021 0.21074 + 0.05; recall_micro >= 0.21569; evidence validity >= 0.90; >=95% successful calls'};common.write_json(out/'config.json',cfg);common.write_json(out/'plan.json',plan);common.write_jsonl(out/'inputs.jsonl',prepared)
 if estimate>cfg['max_cost_usd']:raise RuntimeError('cost ceiling')
 if z.mode=='preflight':print(json.dumps({'status':'preflight_ok',**plan},ensure_ascii=False,indent=2));return
 ck=out/'checkpoint.jsonl';done={(q['id'],q['family']):q for q in readj(ck)} if ck.exists() else {}
 def run(q):
  res={'raw_response':'','model':cfg['model'],'usage':{},'latency_seconds':0.,'finish_reason':None,'success':False}
  try:
   c=common.completion(cfg,q['messages'],base.schema(q['items']));res.update({'raw_response':c.content,'model':c.model,'usage':c.usage,'latency_seconds':c.latency_seconds,'finish_reason':c.finish_reason});j,w=base.post(c.content,records[q['id']],q['items']);res['success']=True
  except Exception as e:j={i:{'위반여부':0,'근거문구':''} for i in q['items']};w=[f'failure:{type(e).__name__}:{str(e)[:200]}']
  return {'id':q['id'],'family':q['family'],'judgment':j,'response':res,'warnings':w}
 rem=[q for q in prepared if(q['id'],q['family'])not in done]
 with ThreadPoolExecutor(max_workers=cfg['concurrency']) as ex:
  fs=[ex.submit(run,q) for q in rem]
  for k,f in enumerate(as_completed(fs),1):x=f.result();done[(x['id'],x['family'])]=x;append(ck,x);print(f'[{k}/{len(rem)}] completed',flush=True) if k%20==0 or k==len(rem) else None
 rows=[]
 for rid in sorted(records):
  j=common.zero_judgment()
  for family in base.FAMILIES:j.update(done[(rid,family)]['judgment'])
  rows.append(common.to_row(rid,j))
 m,per=metric(rows,labels,records);metrics={'experiment_id':cfg['experiment_id'],'request_count':len(done),'successful_request_count':sum(q['response']['success']for q in done.values()),'reported_cost_usd':sum(float(q['response']['usage'].get('cost',0)or 0)for q in done.values()),'metrics':m,'per_item':per};metrics['success_gate_pass']=m['macro_f1']>.26074 and m['recall_micro']>=.21569 and(m['evidence_validity']or 0)>=.90 and metrics['successful_request_count']>=len(prepared)*.95
 with(out/'predictions.csv').open('w',encoding='utf-8',newline='')as h:w=csv.DictWriter(h,fieldnames=common.CSV_COLUMNS,lineterminator='\n');w.writeheader();w.writerows(rows)
 common.write_jsonl(out/'responses.jsonl',[{'id':x['id'],'family':x['family'],**x['response'],'warnings':x['warnings']}for x in done.values()]);common.write_json(out/'metrics.json',metrics);print(json.dumps({'status':'complete','metrics':metrics},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
