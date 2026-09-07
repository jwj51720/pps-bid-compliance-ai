#!/usr/bin/env python3
from __future__ import annotations
import argparse,concurrent.futures,csv,gzip,json,os,re,time
from pathlib import Path
import requests
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[2];RAW=ROOT/'data/raw/open';CARDS=ROOT/'incubator/reference/dev_history/decision_cards_v6.json';PRODUCTS=ROOT/'incubator/data/derived/historical_exp014/competition_products_v1.json';MAN=ROOT/'incubator/runs/inc085_fact_ledger_adjudication_dev64/manifest.jsonl';ITEMS=('v12','v14','v15','v17')
def schema():return {'type':'object','additionalProperties':False,'required':list(ITEMS),'properties':{i:{'type':'integer','enum':[0,1]} for i in ITEMS}}
def status(meta,p):
 codes=re.findall(r'\d{10}',str(meta.get('세부품명번호목록') or ''))
 if not codes:return {'status':'unknown_no_exact_code','matched_products':[]}
 m=[{'code':x,'name':p[x]['세부품명']} for x in codes if x in p]
 return {'status':'competition_product_matched' if m else 'general_product_exact_nonmatch','matched_products':m}
def msg(r,c,p):
 legal='\n\n'.join(f'[{i}|{c[i]["item_name"]}]\n{c[i]["prompt_text"]}' for i in ITEMS); docs='\n\n'.join(f'[{d["type"]}|{d["doc_id"]}]\n{d["text"]}' for d in r['docs'])
 s='''당신은 일반제품 관련 입찰제한(v12,v14,v15,v17)만 검토한다. 정확 제품코드 상태는 organizer 제공 경쟁제품 CSV의 사실이다. general_product_exact_nonmatch는 경쟁제품이 아닌 일반제품이라는 전제를 충족한다. competition_product_matched는 일반제품 전제를 부정한다. unknown_no_exact_code는 일반제품으로 추정하지 않는다. 각 항목에서 제품 전제, 금액구간, 실제 참가자격 제한, 예외를 독립 확인한다. metadata의 조항호내용·제한 분류는 적용성 보조 사실일 뿐 원문에 없는 참가자격 제한을 만들어내지 않는다. 중소기업 일반언급·사후의무도 실제 참가자격 제한이 아니다. 실제 제한은 원문이 중소기업/소기업/소상공인 확인 또는 자격을 입찰참가 조건으로 명시할 때만 인정한다. JSON만 출력한다.'''
 return [{'role':'system','content':s},{'role':'user','content':'[카드]\n'+legal+'\n\n[정확 제품코드 상태]\n'+json.dumps(status(r['meta'],p),ensure_ascii=False)+'\n\n[metadata]\n'+json.dumps(r['meta'],ensure_ascii=False,sort_keys=True)+'\n\n[원문]\n'+docs}]
def text(b):return b.get('output_text') or ''.join(z.get('text','') for x in b.get('output',[]) if x.get('type')=='message' for z in x.get('content',[]) if z.get('type')=='output_text')
def call(k,m):
 p={'model':'gpt-5.6-luna','input':m,'max_output_tokens':8192,'store':False,'reasoning':{'effort':'high'},'text':{'format':{'type':'json_schema','name':'inc113_general_product','strict':True,'schema':schema()}}}
 try:
  q=requests.post('https://api.openai.com/v1/responses',headers={'Authorization':'Bearer '+k,'Content-Type':'application/json'},json=p,timeout=360);b=q.json();t=text(b);return {'success':bool(q.ok and t),'labels':json.loads(t) if q.ok and t else None,'error':'' if q.ok and t else f'{q.status_code}:{b.get("status")}:{b.get("incomplete_details")}', 'raw_response':t}
 except Exception as e:return {'success':False,'error':f'{type(e).__name__}:{e}'}
def f1(pred,gold):
 out={}
 for i in ITEMS:
  tp=fp=fn=0
  for rid,x in pred.items():
   y=int(gold[rid][i]);v=x[i];tp+=v==y==1;fp+=v==1 and not y;fn+=not v and y
  out[i]={'tp':tp,'fp':fp,'fn':fn,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0}
 return sum(x['f1'] for x in out.values())/4,out
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--start',type=int,default=0);ap.add_argument('--size',type=int,default=16);ap.add_argument('--run-id',default='inc113_general_product_specialist');a=ap.parse_args();ids=[x['id'] for x in (json.loads(y) for y in MAN.read_text(encoding='utf8').splitlines())][a.start:a.start+a.size]
 with gzip.open(RAW/'dev.jsonl.gz','rt',encoding='utf8') as h:rec={x['id']:x for x in (json.loads(y) for y in h if y)}
 cards=json.loads(CARDS.read_text(encoding='utf8'))['cards'];prod=json.loads(PRODUCTS.read_text(encoding='utf8'))['products'];load_dotenv(ROOT/'.env');k=os.environ['OPENAI_API_KEY'];out=ROOT/'incubator/runs'/a.run_id;out.mkdir(parents=True,exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
  fs={ex.submit(call,k,msg(rec[r],cards,prod)):r for r in ids};rows=[]
  for f in concurrent.futures.as_completed(fs):
   x=f.result();x['id']=fs[f];rows.append(x)
 (out/'responses.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n',encoding='utf8');gold={x['id']:x for x in csv.DictReader((RAW/'dev_labels.csv').open(encoding='utf8'))};ok={x['id']:x['labels'] for x in rows if x['success']};report={'ids':ids,'success':len(ok),'family_macro':f1(ok,gold)[0] if len(ok)==len(ids) else None,'per_item':f1(ok,gold)[1] if len(ok)==len(ids) else {}};(out/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
