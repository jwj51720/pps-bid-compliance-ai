#!/usr/bin/env python3
"""Concurrent prompt-position ablation; no hidden-thought output requested."""
from __future__ import annotations
import argparse,csv,fcntl,json
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
import inc001_simple_joint24 as c
import inc006_input_budget_ablation as m

CONTRACT="""[최종 판정 지시]
위 metadata와 문서 원문만으로 v1~v24를 서로 독립적으로 판정하라. 키워드만으로 위반을 단정하지 말고 실제 제한·부재·불일치가 있을 때만 1로 둔다. non-absence 항목을 1로 둘 때에는 제공 문서의 변경 없는 연속 substring을 근거로 제시할 수 있을 때만 1로 둔다. 내부 검토 후 JSON 객체 하나만 출력하라."""
def app(p,x):
 with p.open('a',encoding='utf-8') as h:h.write(json.dumps(x,ensure_ascii=False)+'\n');h.flush()
def main():
 a=argparse.ArgumentParser();a.add_argument('--config',default='incubator/configs/inc012_gemma_end_contract.json');a.add_argument('--mode',choices=('preflight','run'),default='preflight');z=a.parse_args();root=c.repo_root();cfg=json.loads((root/z.config).read_text());load_dotenv(root/'.env');out=root/'incubator/runs'/cfg['experiment_id'];out.mkdir(parents=True,exist_ok=True);lock=(out/'.run.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 data=root/cfg['data_root'];recs=c.read_jsonl_gz(data/'dev.jsonl.gz');by={r['id']:r for r in recs};lr=c.read_csv(data/'dev_labels.csv');labels={r['id']:r for r in lr};items=json.loads((data/'data/항목표.json').read_text())['항목'];hist=c.load_historical_false_positives(root/cfg['historical_prediction_path'],labels);cohort,_=c.select_cohort(lr,hist,cfg['positive_seed_limit'],cfg['hard_negative_limit']);sys=c.build_system_prompt(items);req=[]
 for x in cohort:
  r=by[x['id']];msg,render=c.build_messages(r,sys,cfg['document_chars']);req.append({'id':r['id'],'policy':'control','messages':msg,'rendering':render});t=[dict(q) for q in msg];t[1]['content']+='\n\n'+CONTRACT;req.append({'id':r['id'],'policy':'end_contract','messages':t,'rendering':render})
 plan={'experiment_id':cfg['experiment_id'],'cohort_count':len(cohort),'requests':len(req),'changed':'only final user decision contract','success_gate':'macro_f1 +0.02; recall/evidence non-decrease'};c.write_json(out/'config.json',cfg);c.write_json(out/'plan.json',plan);c.write_jsonl(out/'inputs.jsonl',req)
 if z.mode=='preflight':print(json.dumps({'status':'preflight_ok',**plan},ensure_ascii=False));return
 ck=out/'checkpoint.jsonl';done={(q['id'],q['policy']):q for q in ([json.loads(x) for x in ck.read_text().splitlines()] if ck.exists() else [])};rem=[q for q in req if (q['id'],q['policy']) not in done]
 def run(q):
  res=None
  try:
   x=c.completion(cfg,q['messages'],c.judgment_schema());res={'raw_response':x.content,'model':x.model,'usage':x.usage,'latency_seconds':x.latency_seconds,'finish_reason':x.finish_reason,'success':False};j,w=c.postprocess(c.parse_json(x.content),by[q['id']]);row=c.to_row(q['id'],j);res['success']=True
  except Exception as e:
   res=res or {'raw_response':'','model':cfg['model'],'usage':{},'latency_seconds':0,'finish_reason':None,'success':False};row=c.to_row(q['id'],c.zero_judgment());w=[f'failure:{type(e).__name__}:{str(e)[:200]}']
  return {'id':q['id'],'policy':q['policy'],'row':row,'response':res,'warnings':w}
 with ThreadPoolExecutor(max_workers=cfg['concurrency']) as ex:
  fs=[ex.submit(run,q) for q in rem]
  for i,f in enumerate(as_completed(fs),1):
   e=f.result();done[(e['id'],e['policy'])]=e;app(ck,e);print(f'[{i}/{len(rem)}] {e["policy"]}',flush=True)
 rows=defaultdict(list)
 for e in done.values():rows[e['policy']].append(e['row'])
 met={'experiment_id':cfg['experiment_id'],'request_count':len(done),'successful_request_count':sum(e['response']['success'] for e in done.values()),'reported_cost_usd':sum(float(e['response']['usage'].get('cost',0)or 0) for e in done.values()),'policies':{},'per_item':{}}
 for p in ('control','end_contract'):
  met['policies'][p],met['per_item'][p]=m.metric(sorted(rows[p],key=lambda x:x['id']),labels,by)
 A,B=met['policies']['control'],met['policies']['end_contract'];met['delta']={k:B[k]-A[k] for k in ('macro_f1','tp','fp','fn','recall_micro','evidence_validity')};c.write_jsonl(out/'responses.jsonl',[{'id':e['id'],'policy':e['policy'],**e['response'],'warnings':e['warnings']} for e in done.values()]);c.write_json(out/'metrics.json',met);print(json.dumps({'status':'complete','metrics':met},ensure_ascii=False))
if __name__=='__main__':main()
