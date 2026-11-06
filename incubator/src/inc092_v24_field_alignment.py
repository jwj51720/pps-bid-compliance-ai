#!/usr/bin/env python3
"""Full-context, one-item v24 field-alignment diagnostic (no heuristic rules)."""
from __future__ import annotations
import argparse, concurrent.futures, csv, gzip, json, os, time
from pathlib import Path
import requests
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[2]; DATA=ROOT/'data/raw/open'; OUT=ROOT/'incubator/runs/inc092_v24_field_alignment_dev200'; CARD=ROOT/'incubator/reference/dev_history/decision_cards_v6.json'
def readgz(p):
 with gzip.open(p,'rt',encoding='utf8') as h:return [json.loads(x) for x in h if x]
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf8').splitlines() if x]
def schema():
 field={'type':'object','additionalProperties':False,'required':['status','quote'],'properties':{'status':{'type':'string','enum':['match','contradiction','source_missing','not_comparable']},'quote':{'type':'string','maxLength':500}}}
 return {'type':'object','additionalProperties':False,'required':['budget','contract_method','region_restriction','industry_restriction','v24'],'properties':{'budget':field,'contract_method':field,'region_restriction':field,'industry_restriction':field,'v24':{'type':'integer','enum':[0,1]}}}
def docs(r):return '\n\n'.join(f'[{d["type"]}|{d["doc_id"]}]\n{d["text"]}' for d in r['docs'])
def msg(r,card):
 system='''당신은 나라장터 metadata와 공고 원문 간 v24 불일치를 엄밀히 검사한다. 비교 필드는 오직 예산, 계약방법, 참가자격 지역제한, 참가자격 업종제한이다. 각 필드마다 원문에 대응 값이 명시되면 metadata의 같은 필드와 비교한다. 표현·분류 차이, 문서의 일반 지역 언급, 다른 필드, 원문 미기재는 모순이 아니다. status=contradiction은 같은 필드의 실제 값이 양립 불가능할 때만 쓴다. quote는 source_missing/not_comparable이면 빈 문자열, match/contradiction이면 판단에 사용한 원문 연속 부분문자열이다. 네 필드 중 하나라도 contradiction일 때만 v24=1이다. JSON만 출력한다.'''
 user='[v24 판단정의]\n'+card['prompt_text']+'\n\n[metadata]\n'+json.dumps(r['meta'],ensure_ascii=False,sort_keys=True)+'\n\n[공고 원문 전체]\n'+docs(r)
 return [{'role':'system','content':system},{'role':'user','content':user}]
def call(key,m):
 p={'model':'gpt-5.6-luna','input':m,'max_output_tokens':8192,'store':False,'reasoning':{'effort':'high'},'text':{'format':{'type':'json_schema','name':'inc092_v24','strict':True,'schema':schema()}}}
 for a in range(4):
  try:
   q=requests.post('https://api.openai.com/v1/responses',headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},json=p,timeout=300);b=q.json();t=b.get('output_text') or ''.join(z.get('text','') for x in b.get('output',[]) if x.get('type')=='message' for z in x.get('content',[]) if z.get('type')=='output_text')
   if q.ok and t:return {'success':True,'value':json.loads(t),'raw_response':t,'usage':b.get('usage',{})}
   err=json.dumps({'status':b.get('status'),'detail':b.get('incomplete_details')},ensure_ascii=False)
  except Exception as e:err=f'{type(e).__name__}:{e}'
  time.sleep(2**a)
 return {'success':False,'error':err}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=('run','score'),default='run');ap.add_argument('--workers',type=int,default=16);a=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True);rs=readgz(DATA/'dev.jsonl.gz');card=json.loads(CARD.read_text(encoding='utf8'))['cards']['v24']
 if a.mode=='run':
  load_dotenv(ROOT/'.env');key=os.getenv('OPENAI_API_KEY');assert key; ck=OUT/'checkpoint.jsonl';done={x['id']:x for x in jl(ck)} if ck.exists() else {};pending=[r for r in rs if not done.get(r['id'],{}).get('success')]
  def one(r):
   x=call(key,msg(r,card));
   if x['success']:
    source='\n'.join(d['text'] for d in r['docs']);v=x.pop('value');valid=[]
    for f in ('budget','contract_method','region_restriction','industry_restriction'):
     if v[f]['status'] in ('match','contradiction') and v[f]['quote'] not in source:valid.append(f)
    x.update({'result':v,'invalid_quote_fields':valid})
   return {'id':r['id'],**x}
  with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
   fs=[ex.submit(one,r) for r in pending]
   for n,f in enumerate(concurrent.futures.as_completed(fs),1):z=f.result();open(ck,'a',encoding='utf8').write(json.dumps(z,ensure_ascii=False)+'\n');print(n,len(fs),z['id'],z['success'],flush=True)
 else:
  gold={x['id']:int(x['v24']) for x in csv.DictReader((DATA/'dev_labels.csv').open(encoding='utf8'))};d={x['id']:x for x in jl(OUT/'checkpoint.jsonl') if x.get('success')};tp=fp=fn=0
  for rid,x in d.items():v=x['result']['v24'];y=gold[rid];tp+=v==y==1;fp+=v==1 and y==0;fn+=v==0 and y==1
  f=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0;print(json.dumps({'success':len(d),'tp':tp,'fp':fp,'fn':fn,'f1':f,'invalid_quote_fields':sum(len(x['invalid_quote_fields']) for x in d.values())},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
