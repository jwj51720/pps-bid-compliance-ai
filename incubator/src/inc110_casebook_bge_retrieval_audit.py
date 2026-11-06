#!/usr/bin/env python3
"""BGE-M3 retrieval audit over unlabeled-only casebook records."""
from __future__ import annotations
import gzip,json,math,os,re
from pathlib import Path
import requests
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[2];RAW=ROOT/'data/raw/open';CASE=ROOT/'incubator/runs/inc108_unlabeled_casebook64';OUT=ROOT/'incubator/runs/inc110_casebook_bge_retrieval_audit'
FIELDS=('적용계약법','업무구분','계약방법','낙찰방법','조항호내용','세부품명번호목록','제한지역코드목록','면허업종제한목록','배정예산금액','입찰추정가격','정보화사업여부')
def profile(meta,s=''):return '\n'.join(f'{k}: {meta.get(k) or ""}' for k in FIELDS)+'\n사례요약: '+s
def embed(key,values):
 q=requests.post('https://openrouter.ai/api/v1/embeddings',headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},json={'model':'baai/bge-m3','input':values,'encoding_format':'float'},timeout=180)
 if not q.ok:raise RuntimeError(f'{q.status_code}:{q.text[:300]}')
 b=q.json();rows=sorted(b['data'],key=lambda x:x['index']);return [x['embedding'] for x in rows],b.get('usage',{})
def cos(a,b):return sum(x*y for x,y in zip(a,b))/(math.sqrt(sum(x*x for x in a))*math.sqrt(sum(y*y for y in b)) or 1)
def main():
 a={x['id']:x for x in (json.loads(y) for y in (CASE/'stage_a.jsonl').read_text(encoding='utf8').splitlines()) if x.get('success')}; b={x['id']:x for x in (json.loads(y) for y in (CASE/'stage_b.jsonl').read_text(encoding='utf8').splitlines()) if x.get('success')}
 with gzip.open(RAW/'train_unlabeled.jsonl.gz','rt',encoding='utf8') as h:train={x['id']:x for x in (json.loads(y) for y in h if y) if x['id'] in a and x['id'] in b}
 with gzip.open(RAW/'dev.jsonl.gz','rt',encoding='utf8') as h:dev=[json.loads(y) for y in h if y]
 cases=[]
 for rid in train:
  v=a[rid]['value'];
  if re.fullmatch(r'D\d+(?:-D\d+)*',v['case_signature'].strip()):continue
  pos=[i for i,x in v['labels'].items() if x];ev=b[rid]['value']['evidence'];cases.append({'id':rid,'text':profile(train[rid]['meta'],v['case_signature']),'signature':v['case_signature'],'labels':v['labels'],'positive_bases':{i:ev[i]['basis'] for i in pos}})
 load_dotenv(ROOT/'.env');key=os.environ['OPENROUTER_API_KEY'];cv,u1=embed(key,[x['text'] for x in cases]);qv,u2=embed(key,[profile(x['meta']) for x in dev]);rows=[]
 for r,v in zip(dev,qv):
  rank=sorted(((cos(v,cv[i]),i) for i in range(len(cases))),reverse=True)[:3];rows.append({'id':r['id'],'results':[{'rank':n+1,'id':cases[i]['id'],'score':round(s,5),'signature':cases[i]['signature'],'positive_labels':[k for k,z in cases[i]['labels'].items() if z],'positive_bases':cases[i]['positive_bases']} for n,(s,i) in enumerate(rank)]})
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'retrieval.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n',encoding='utf8');report={'case_count':len(cases),'dev_queries':len(rows),'usage':[u1,u2],'mean_top1_score':sum(x['results'][0]['score'] for x in rows)/len(rows),'top3_cases_with_positive':sum(bool(x['positive_labels']) for r in rows for x in r['results'])/(len(rows)*3)};(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
