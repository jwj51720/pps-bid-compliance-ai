#!/usr/bin/env python3
"""INC-087: full-context Luna decisions with explicit same-call evidence."""
from __future__ import annotations
import argparse, concurrent.futures, csv, json, os, time
from pathlib import Path
from typing import Any
import requests
from dotenv import load_dotenv
import inc001_simple_joint24 as common
import inc081_teacher_full_context_calibration as calibration

ROOT=Path(__file__).resolve().parents[2]; DATA=ROOT/'data/raw/open'; RUN=ROOT/'incubator/runs/inc087_direct_evidence_report_dev64'; MANIFEST=ROOT/'incubator/runs/inc085_fact_ledger_adjudication_dev64/manifest.jsonl'; CARDS=ROOT/'incubator/reference/dev_history/decision_cards_v6.json'; ITEMS=common.ITEMS

def rows(path:Path)->list[dict[str,Any]]: return [json.loads(x) for x in path.read_text(encoding='utf8').splitlines() if x]
def schema():
 entry={'type':'object','additionalProperties':False,'required':['v','basis','quote'],'properties':{'v':{'type':'integer','enum':[0,1]},'basis':{'type':'string','maxLength':240},'quote':{'type':'string','maxLength':500}}}
 return {'type':'object','additionalProperties':False,'required':list(ITEMS),'properties':{i:entry for i in ITEMS}}
def core(cards): return '\n\n'.join(f'[{i} | {c["item_name"]}]\n{c["prompt_text"]}' for i,c in cards['cards'].items())
def messages(r,cards):
 system='''당신은 한국 공공입찰 법령 위반을 판정하는 독립 검토자다. 제공된 모든 공고 원문·메타·법령 판단 핵심만 사용한다. 각 항목을 적용대상→공고 사실→수치/제한/예외→결론 순서로 검토한다. 키워드만으로 단정하지 않는다. 각 항목에 v, basis, quote를 출력한다. basis는 결론을 좌우한 짧은 판단 이유다. v=1이면 quote는 반드시 그 판단을 뒷받침하는 공고 원문의 변경 없는 연속 부분문자열이어야 한다. v=0이면 quote는 빈 문자열이다. [부재탐지]는 적용대상임이 확인된 뒤 공고 전체에서 필요한 조건이 없을 때만 1이다. 최종 JSON 하나만 출력한다.'''
 user='\n\n'.join(['[항목별 법령 판단 핵심]\n'+core(cards),'[나라장터 메타]\n'+json.dumps(r['meta'],ensure_ascii=False,sort_keys=True),'[공고 원문 전체]\n'+calibration.render_documents(r)])
 return [{'role':'system','content':system},{'role':'user','content':user}]
def call(key,msg):
 payload={'model':'gpt-5.6-luna','input':msg,'max_output_tokens':4096,'store':False,'text':{'format':{'type':'json_schema','name':'inc087_report','strict':True,'schema':schema()}}}
 for attempt in range(4):
  start=time.monotonic()
  try:
   resp=requests.post('https://api.openai.com/v1/responses',headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},json=payload,timeout=240); body=resp.json()
   if resp.ok:
    text=body.get('output_text') or ''.join(b.get('text','') for m in body.get('output',[]) if m.get('type')=='message' for b in m.get('content',[]) if b.get('type')=='output_text')
    if text: return {'success':True,'value':json.loads(text),'raw_response':text,'usage':body.get('usage',{}),'latency_seconds':round(time.monotonic()-start,3)}
    error=json.dumps({'status':body.get('status'),'incomplete_details':body.get('incomplete_details')},ensure_ascii=False)
   else: error=f'HTTP {resp.status_code}: {resp.text[:400]}'
  except (requests.RequestException,ValueError,KeyError,json.JSONDecodeError) as e: error=f'{type(e).__name__}: {e}'
  time.sleep(2**attempt)
 return {'success':False,'error':error,'raw_response':'','usage':{},'latency_seconds':0}
def validate(value,r):
 if not isinstance(value,dict) or set(value)!=set(ITEMS): raise ValueError('schema')
 source='\n'.join(d['text'] for d in r['docs']); report={}; invalid=[]
 for i in ITEMS:
  x=value[i]
  if not isinstance(x,dict) or set(x)!={'v','basis','quote'} or x['v'] not in(0,1): raise ValueError(i)
  basis=x['basis'].strip(); quote=x['quote'].strip(); valid=(not x['v']) or bool(quote) and quote in source
  invalid += [i] if x['v'] and not valid else []
  report[i]={'v':int(x['v']),'basis':basis,'quote':quote,'quote_valid':valid}
 return report,invalid
def f1(pred,gold):
 out=[]
 for i in ITEMS:
  tp=fp=fn=0
  for rid,x in pred.items():
   y=int(gold[rid][i]); v=x[i]; tp+=v==y==1; fp+=v==1 and y==0; fn+=v==0 and y==1
  out.append({'item':i,'tp':tp,'fp':fp,'fn':fn,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0})
 return sum(x['f1'] for x in out)/24,out
def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=('run','aggregate'),default='run');p.add_argument('--workers',type=int,default=4);a=p.parse_args(); RUN.mkdir(parents=True,exist_ok=True)
 manifest=rows(MANIFEST); rec={x['id']:x for x in common.read_jsonl_gz(DATA/'dev.jsonl.gz')}; cards=json.loads(CARDS.read_text(encoding='utf8'))
 if a.mode=='run':
  load_dotenv(ROOT/'.env');key=os.getenv('OPENAI_API_KEY'); assert key
  ck=RUN/'checkpoint.jsonl'; latest={x['id']:x for x in rows(ck)} if ck.exists() else {}; pending=[x for x in manifest if not latest.get(x['id'],{}).get('success')]
  def one(m):
   r=rec[m['id']]; ans=call(key,messages(r,cards))
   if ans['success']:
    try: ans['report'],ans['invalid_positive_quote_items']=validate(ans.pop('value'),r)
    except ValueError as e: ans={'success':False,'error':str(e),'raw_response':ans['raw_response'],'usage':ans['usage'],'latency_seconds':ans['latency_seconds']}
   return {'id':m['id'],**ans}
  with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
   fs=[ex.submit(one,m) for m in pending]
   for n,f in enumerate(concurrent.futures.as_completed(fs),1): common.append_jsonl(ck,f.result());print(f'[{n}/{len(fs)}] {f.result()["id"]}',flush=True)
 else:
  ck=rows(RUN/'checkpoint.jsonl'); latest={x['id']:x for x in ck}; ok={k:v for k,v in latest.items() if v.get('success')}; gold={x['id']:x for x in csv.DictReader((DATA/'dev_labels.csv').open(encoding='utf8'))}; raw={rid:{i:x['report'][i]['v'] for i in ITEMS} for rid,x in ok.items()}; gated={rid:{i:x['report'][i]['v'] if (not x['report'][i]['v'] or x['report'][i]['quote_valid']) else 0 for i in ITEMS} for rid,x in ok.items()}; m,per=f1(raw,gold); gm,gper=f1(gated,gold); direct={x['id']:x['labels'] for x in rows(ROOT/'incubator/runs/inc084_openai_luna_full_dev_card/responses.jsonl')}; dm,_=f1({rid:direct[rid] for rid in ok},gold); result={'complete':len(ok),'raw_report_macro_f1':m,'quote_gated_macro_f1':gm,'direct_label_only_same_cohort_macro_f1':dm,'invalid_positive_quotes':sum(len(x.get('invalid_positive_quote_items',[])) for x in ok.values()),'per_item':per,'gated_per_item':gper}; common.write_json(RUN/'metrics.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
