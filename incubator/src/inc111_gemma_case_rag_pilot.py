#!/usr/bin/env python3
from __future__ import annotations
import argparse,concurrent.futures,csv,gzip,json,os
from pathlib import Path
from dotenv import load_dotenv
import inc001_simple_joint24 as common
import inc081_teacher_full_context_calibration as cal
ROOT=Path(__file__).resolve().parents[2];RAW=ROOT/'data/raw/open';MAN=ROOT/'incubator/runs/inc085_fact_ledger_adjudication_dev64/manifest.jsonl';RET=ROOT/'incubator/runs/inc110_casebook_bge_retrieval_audit/retrieval.jsonl';CARDS=ROOT/'incubator/reference/dev_history/decision_cards_v6.json';OUT=ROOT/'incubator/runs/inc111_gemma_case_rag_pilot';ITEMS=common.ITEMS
def schema():return {'type':'object','additionalProperties':False,'required':list(ITEMS),'properties':{i:{'type':'integer','enum':[0,1]} for i in ITEMS}}
def msg(r,cases,cards):
 core='\n\n'.join(f'[{i}|{x["item_name"]}]\n{x["prompt_text"]}' for i,x in cards['cards'].items())
 s='공공입찰 법령 위반을 독립 판정한다. 현재 공고 원문과 metadata가 유일한 결론 근거다. 사례는 참고 선례일 뿐 현재 공고에 라벨을 전이하지 않는다. 적용대상, 실제 참가자격, 예외와 원문 사실을 항목별로 확인하고 JSON만 출력한다.'
 parts=['[카드]\n'+core,'[metadata]\n'+json.dumps(r['meta'],ensure_ascii=False,sort_keys=True)]
 if cases:parts.append('[unlabeled 참고 사례]\n'+json.dumps(cases,ensure_ascii=False))
 parts.append('[현재 공고 원문 전체]\n'+cal.render_documents(r))
 return [{'role':'system','content':s},{'role':'user','content':'\n\n'.join(parts)}]
def score(p,g):
 vals=[]
 for i in ITEMS:
  tp=fp=fn=0
  for rid,x in p.items():
   y=int(g[rid][i]);v=x[i];tp+=v==y==1;fp+=v==1 and not y;fn+=not v and y
  vals.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0)
 return sum(vals)/24
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--start',type=int,default=0);ap.add_argument('--size',type=int,default=8);ap.add_argument('--run-id',default='inc111_gemma_case_rag_pilot');args=ap.parse_args()
 ids=[x['id'] for x in (json.loads(y) for y in MAN.read_text(encoding='utf8').splitlines())][args.start:args.start+args.size]
 with gzip.open(RAW/'dev.jsonl.gz','rt',encoding='utf8') as h:rec={x['id']:x for x in (json.loads(y) for y in h if y)}
 gold={x['id']:x for x in csv.DictReader((RAW/'dev_labels.csv').open(encoding='utf8'))};cards=json.loads(CARDS.read_text(encoding='utf8'));retr={x['id']:x['results'] for x in (json.loads(y) for y in RET.read_text(encoding='utf8').splitlines())};load_dotenv(ROOT/'.env');output=ROOT/'incubator/runs'/args.run_id;output.mkdir(parents=True,exist_ok=True)
 cfg={'model':'google/gemma-4-26b-a4b-it','api_url':'https://openrouter.ai/api/v1/chat/completions','api_key_env':'OPENROUTER_API_KEY','temperature':0.,'seed':20260905,'max_tokens':1200,'timeout_seconds':240,'request_retries':1}
 def one(rid,arm):
  try:
   z=common.completion(cfg,msg(rec[rid],retr[rid] if arm=='rag' else [],cards),schema());v=common.parse_json(z.content);assert set(v)==set(ITEMS) and all(v[i] in(0,1) for i in ITEMS);return {'id':rid,'arm':arm,'success':True,'labels':v,'usage':z.usage}
  except Exception as e:return {'id':rid,'arm':arm,'success':False,'error':str(e)}
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
  fs=[ex.submit(one,rid,arm) for rid in ids for arm in ('direct','rag')];rows=[f.result() for f in concurrent.futures.as_completed(fs)]
 (output/'responses.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n',encoding='utf8');d={x['id']:x['labels'] for x in rows if x['success'] and x['arm']=='direct'};r={x['id']:x['labels'] for x in rows if x['success'] and x['arm']=='rag'};report={'ids':ids,'direct_success':len(d),'rag_success':len(r),'direct_macro':score(d,gold) if len(d)==len(ids) else None,'rag_macro':score(r,gold) if len(r)==len(ids) else None};report['delta']=report['rag_macro']-report['direct_macro'] if report['direct_macro'] is not None and report['rag_macro'] is not None else None;(output/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
