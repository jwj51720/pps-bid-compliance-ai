#!/usr/bin/env python3
"""INC-073: semantic e-prime extraction with direct-judgment fallback."""
from __future__ import annotations
import argparse, hashlib, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import inc001_simple_joint24 as common
import inc018_global_context_architecture as context

ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'incubator/runs/inc073_eprime_hybrid_pilot'

def load():
 d=ROOT/'data/raw/open'; rs={x['id']:x for x in common.read_jsonl_gz(d/'dev.jsonl.gz')}; ls={x['id']:x for x in common.read_csv(d/'dev_labels.csv')}; cs=json.loads((ROOT/'incubator/data/derived/legal_essence_cards_v1.json').read_text())['cards']; return rs,ls,cs
def items(cs): return tuple(x for x in common.ITEMS if x in cs)
def cohort(rs,ls,it):
 s=set()
 for x in it: s.add(min((rid for rid in rs if ls[rid][x]=='1'),key=lambda rid:hashlib.sha256(f'inc073:{x}:{rid}'.encode()).hexdigest()))
 rem=sorted((rid for rid in rs if rid not in s),key=lambda rid:hashlib.sha256(f'inc073:r:{rid}'.encode()).hexdigest());s.update(rem[:20-len(s)]);return sorted(s)
def cfg(tokens): return {'model':'google/gemma-4-26b-a4b-it','api_url':'https://openrouter.ai/api/v1/chat/completions','api_key_env':'OPENROUTER_API_KEY','temperature':0.0,'seed':20260905,'max_tokens':tokens,'timeout_seconds':120,'request_retries':1}
def card_block(cs,it): return {x:{'항목명':cs[x]['item_definition']['항목명'],**cs[x]['card']} for x in it}
def direct_schema(it): return {'type':'object','additionalProperties':False,'required':list(it),'properties':{x:{'type':'object','additionalProperties':False,'required':['v','e'],'properties':{'v':{'type':'integer','enum':[0,1]},'e':{'type':['string','null'],'maxLength':500}}} for x in it}}
def flat_schema(it): return {'type':'object','additionalProperties':False,'required':list(it),'properties':{x:{'type':['string','null']} for x in it}}
def label_schema(it): return {'type':'object','additionalProperties':False,'required':list(it),'properties':{x:{'type':'integer','enum':[0,1]} for x in it}}
def definitions(cs,it): return '\n'.join(f'- {x}: {cs[x]["item_definition"]["항목명"]}' + (' [부재탐지]' if x in common.ABSENCE_ITEMS else '') for x in it)
def direct_messages(r,cs,it):
 sys='\n'.join(['당신은 공공입찰 공고의 법령 위반을 판단한다. 모든 원문과 메타를 읽고 키워드만으로 단정하지 않는다.','v=1인 non-absence e는 원문의 변경 없는 연속 부분문자열 500자 이하여야 하며, 0이면 null이다. 부재탐지는 e=null이다.','판정 항목:',definitions(cs,it),'JSON 하나만 출력한다.'])
 return [{'role':'system','content':sys},{'role':'user','content':'[메타]\n'+json.dumps(r['meta'],ensure_ascii=False,sort_keys=True)+'\n\n[전체 문서]\n'+context.full_context(r)}]
def extract_messages(r,cs,it):
 sys='\n'.join(['당신은 공공입찰 원문에서 판단 관련 사실을 추출한다. 각 항목별로 법령 판단 엑기스에 맞는 공고 사실을 1~2문장으로 의미 요약한다.','원문의 직접 인용이나 위반판정은 하지 않는다. 적용 전제·제한·예외·금액·절차 중 판단할 사실이 전혀 없을 때만 null이다. null은 무위반 뜻이 아니다.','JSON 하나만 출력한다.'])
 user='[항목별 법령 판단 엑기스]\n'+json.dumps(card_block(cs,it),ensure_ascii=False)+'\n\n[메타]\n'+json.dumps(r['meta'],ensure_ascii=False,sort_keys=True)+'\n\n[전체 문서]\n'+context.full_context(r)
 return [{'role':'system','content':sys},{'role':'user','content':user}]
def adjudicate_messages(eprime,cs,it):
 sys='\n'.join(['당신은 법령 판단 엑기스와 공고 사실 요약만으로 각 항목의 위반을 판단한다.','null e-prime은 판단하지 못한 것이므로 0을 임의 확정하지 말고 0을 출력하되, 최종 시스템은 이 값을 사용하지 않는다.','JSON 하나만 출력한다.'])
 return [{'role':'system','content':sys},{'role':'user','content':'[법령 판단 엑기스]\n'+json.dumps(card_block(cs,it),ensure_ascii=False)+'\n\n[e-prime: 비인용 의미 요약]\n'+json.dumps(eprime,ensure_ascii=False)}]
def direct_validate(p,r,it):
 src='\n'.join(x['text'] for x in r['docs']);out={};warn=[]
 for x in it:
  c=p.get(x)
  if not isinstance(c,dict) or c.get('v') not in(0,1):raise ValueError(x)
  v=int(c['v']);e=c.get('e');e=e.strip() if isinstance(e,str) else ''
  if x in common.ABSENCE_ITEMS:e=''
  elif v and e not in src:warn.append(x);v,e=0,''
  elif not v:e=''
  out[x]={'v':v,'e':e}
 return out,warn
def call(stage,rid,rep,rs,cs,it):
 p=OUT/'records'/f'{rid}_{rep}_{stage}.json'
 if p.exists():return
 r=rs[rid];response:Any=None
 try:
  if stage=='direct': response=common.completion(cfg(800),direct_messages(r,cs,it),direct_schema(it));value,w=direct_validate(common.parse_json(response.content),r,it); row={'value':value,'warnings':w}
  elif stage=='extract': response=common.completion(cfg(700),extract_messages(r,cs,it),flat_schema(it));value=common.parse_json(response.content); assert set(value)==set(it) and all(v is None or isinstance(v,str) for v in value.values());row={'value':value}
  else:
   ep=json.loads((OUT/'records'/f'{rid}_{rep}_extract.json').read_text())['value'];response=common.completion(cfg(256),adjudicate_messages(ep,cs,it),label_schema(it));value=common.parse_json(response.content);assert set(value)==set(it) and all(v in(0,1) for v in value.values());row={'value':value}
  entry={'id':rid,'repeat':rep,'stage':stage,'success':True,'usage':response.usage,'raw_response':response.content,**row}
 except Exception as e:entry={'id':rid,'repeat':rep,'stage':stage,'success':False,'error':f'{type(e).__name__}: {e}','usage':{} if response is None else response.usage,'raw_response':'' if response is None else response.content}
 p.parent.mkdir(parents=True,exist_ok=True);common.write_json(p,entry)
def score(pred,ls,ids,it):
 rows=[]
 for x in it:
  tp=fp=fn=0
  for rid in ids:
   g=int(ls[rid][x]);v=int(pred[rid][x]);tp+=g and v;fp+=not g and v;fn+=g and not v
  rows.append({'item':x,'tp':tp,'fp':fp,'fn':fn,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0})
 return {'macro_f1':sum(x['f1'] for x in rows)/len(rows),'tp':sum(x['tp'] for x in rows),'fp':sum(x['fp'] for x in rows),'fn':sum(x['fn'] for x in rows),'per_item':rows}
def preflight():
 rs,ls,cs=load();it=items(cs);ids=cohort(rs,ls,it);OUT.mkdir(parents=True,exist_ok=True);common.write_json(OUT/'config.json',{'items':it,'cohort':len(ids),'repeats':2,'calls':len(ids)*3*2,'max_cost_usd':.45,'promotion':'e-prime positive coverage >= direct-positive coverage; both hybrid-direct deltas positive; source fallback used for every null e-prime'});common.write_jsonl(OUT/'cohort.jsonl',[{'id':rid,'positive':[x for x in it if ls[rid][x]=='1']} for rid in ids]);print(json.dumps({'status':'preflight_ok','cohort':len(ids),'calls':len(ids)*6,'items':it},ensure_ascii=False,indent=2))
def run(workers):
 rs,ls,cs=load();it=items(cs);ids=cohort(rs,ls,it)
 for stage in ('direct','extract','adjudicate'):
  with ThreadPoolExecutor(max_workers=workers) as ex:
   fs=[ex.submit(call,stage,rid,rep,rs,cs,it) for rep in ('r1','r2') for rid in ids]
   for n,f in enumerate(as_completed(fs),1):f.result();print(f'{stage}={n}/{len(fs)}',flush=True)
def aggregate():
 rs,ls,cs=load();it=items(cs);ids=cohort(rs,ls,it);report={'experiment_id':'inc073_eprime_hybrid_pilot','items':it,'cohort_size':len(ids),'repeats':{}}
 for rep in ('r1','r2'):
  sets={s:[json.loads((OUT/'records'/f'{rid}_{rep}_{s}.json').read_text()) for rid in ids] for s in ('direct','extract','adjudicate')}; bad={s:sum(not x['success'] for x in a) for s,a in sets.items()};row={'failures':bad,'cost_usd':sum(float(x.get('usage',{}).get('cost',0)or 0) for a in sets.values() for x in a)}
  if not any(bad.values()):
   direct={x['id']:{k:v['v'] for k,v in x['value'].items()} for x in sets['direct']}; ep={x['id']:x['value'] for x in sets['extract']};adj={x['id']:x['value'] for x in sets['adjudicate']};hybrid={rid:{x:adj[rid][x] if ep[rid][x] is not None and ep[rid][x].strip() else direct[rid][x] for x in it} for rid in ids}; positives=sum(int(ls[rid][x]) for rid in ids for x in it);covered=sum(int(ls[rid][x]) for rid in ids for x in it if ep[rid][x] is not None and ep[rid][x].strip());row.update({'direct':score(direct,ls,ids,it),'hybrid':score(hybrid,ls,ids,it),'hybrid_minus_direct':score(hybrid,ls,ids,it)['macro_f1']-score(direct,ls,ids,it)['macro_f1'],'eprime_positive_coverage':covered/positives if positives else None,'eprime_nonempty_rate':sum(bool(ep[rid][x] and ep[rid][x].strip()) for rid in ids for x in it)/(len(ids)*len(it))})
  report['repeats'][rep]=row
 common.write_json(OUT/'metrics.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',required=True,choices=('preflight','run','aggregate'));p.add_argument('--workers',type=int,default=16);a=p.parse_args();load_dotenv(ROOT/'.env');OUT.mkdir(parents=True,exist_ok=True);{'preflight':preflight,'run':lambda:run(a.workers),'aggregate':aggregate}[a.mode]()
if __name__=='__main__':main()
