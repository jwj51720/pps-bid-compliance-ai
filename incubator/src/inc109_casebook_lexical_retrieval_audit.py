#!/usr/bin/env python3
"""Build a label-free lexical retrieval manifest for the 64-case casebook."""
from __future__ import annotations
import collections,csv,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RUN=ROOT/'incubator/runs/inc108_unlabeled_casebook64';OUT=ROOT/'incubator/runs/inc109_casebook_lexical_retrieval_audit';RAW=ROOT/'data/raw/open'
TOK=re.compile(r'[가-힣A-Za-z0-9]{2,}')
FIELDS=('적용계약법','업무구분','계약방법','낙찰방법','조항호내용','세부품명번호목록','제한지역코드목록','면허업종제한목록','배정예산금액','입찰추정가격','정보화사업여부')
def terms(meta,signature=''):
 text=' '.join(str(meta.get(k) or '') for k in FIELDS)+' '+signature
 return set(TOK.findall(text.lower()))
def main():
 a={x['id']:x for x in (json.loads(y) for y in (RUN/'stage_a.jsonl').read_text(encoding='utf8').splitlines()) if x.get('success')}
 b={x['id']:x for x in (json.loads(y) for y in (RUN/'stage_b.jsonl').read_text(encoding='utf8').splitlines()) if x.get('success')}
 records={x['id']:x for x in (json.loads(y) for y in (RUN/'records.jsonl').read_text(encoding='utf8').splitlines()) if x['id'] in a and x['id'] in b}
 import gzip
 with gzip.open(RAW/'train_unlabeled.jsonl.gz','rt',encoding='utf8') as h:train={x['id']:x for x in (json.loads(y) for y in h if y) if x['id'] in records}
 with gzip.open(RAW/'dev.jsonl.gz','rt',encoding='utf8') as h:dev=[json.loads(y) for y in h if y]
 cases=[]
 for rid,row in records.items():
  value=a[rid]['value']; positives=[i for i,v in value['labels'].items() if v]
  ev=b[rid]['value']['evidence']; cases.append({'id':rid,'profile':terms(train[rid]['meta'],value['case_signature']),'signature':value['case_signature'],'labels':value['labels'],'positive_bases':{i:ev[i]['basis'] for i in positives},'meta':train[rid]['meta']})
 df=collections.Counter(t for c in cases for t in c['profile']);n=len(cases)
 rows=[]
 for r in dev:
  q=terms(r['meta']);rank=[]
  for c in cases:
   shared=q & c['profile'];score=sum((1+(n/df[t])**.5) for t in shared)
   rank.append((score,c,sorted(shared)))
  rank.sort(key=lambda x:(-x[0],x[1]['id']));rows.append({'id':r['id'],'query_terms':sorted(q),'results':[{'rank':k+1,'id':c['id'],'score':round(s,4),'shared_terms':shared,'signature':c['signature'],'positive_labels':[i for i,v in c['labels'].items() if v],'positive_bases':c['positive_bases']} for k,(s,c,shared) in enumerate(rank[:3])]})
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'retrieval.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n',encoding='utf8')
 report={'case_count':len(cases),'dev_queries':len(rows),'top1_zero_overlap':sum(not x['results'][0]['shared_terms'] for x in rows),'mean_top1_shared_terms':sum(len(x['results'][0]['shared_terms']) for x in rows)/len(rows),'source':'unlabeled casebook only'};(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
