#!/usr/bin/env python3
from __future__ import annotations
import json,os
from pathlib import Path
import requests
from dotenv import load_dotenv
import inc001_simple_joint24 as common
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'incubator/runs/inc059_large_candidate_transport_audit';ABS={'v10','v11','v16','v18','v20'}
def main():
 load_dotenv(ROOT/'.env');OUT.mkdir(parents=True,exist_ok=True);p=OUT/'responses.jsonl';rows=[json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
 fields={f'v{i}':{'type':'integer','enum':[0,1]} for i in range(1,25)};ev=[f'e{i}' for i in range(1,25) if f'v{i}' not in ABS];fields.update({x:{'type':'integer','enum':[-1,*range(768)]} for x in ev});expected={x:0 for x in fields};expected['v1']=1;expected['e1']=511
 schema={'type':'object','additionalProperties':False,'required':list(fields),'properties':fields};key=os.environ['OPENROUTER_API_KEY']
 for n in range(len(rows)+1,6):
  body={'model':'google/gemma-4-26b-a4b-it','messages':[{'role':'user','content':'JSON 하나만 출력. v1=1,e1=511, 나머지 모든 필드는 0, 모든 e 필드는 -1.'}],'temperature':0,'seed':20260905,'max_tokens':128,'provider':{'require_parameters':True,'sort':'throughput'},'response_format':{'type':'json_schema','json_schema':{'name':'large_flat','strict':True,'schema':schema}}}
  try:
   r=requests.post('https://openrouter.ai/api/v1/chat/completions',headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},json=body,timeout=120);b=r.json();c=b['choices'][0]['message']['content'];u=b.get('usage',{});ok=json.loads(c)==expected and int(u.get('completion_tokens',0)or 0)<=128;rows.append({'n':n,'success':ok,'completion_tokens':u.get('completion_tokens'),'usage':u,'content':c})
  except Exception as e:rows.append({'n':n,'success':False,'error':str(e),'usage':{}})
  common.write_jsonl(p,rows)
 report={'experiment_id':'inc059_large_candidate_transport_audit','calls':len(rows),'valid':sum(x['success'] for x in rows),'cap_breaches':sum((x.get('completion_tokens')or 0)>128 for x in rows),'advance':len(rows)==5 and all(x['success'] for x in rows),'cost':sum(float(x.get('usage',{}).get('cost',0)or 0) for x in rows)};common.write_json(OUT/'report.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
