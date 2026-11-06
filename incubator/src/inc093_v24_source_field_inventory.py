#!/usr/bin/env python3
"""Inventory exact source candidates for v24 fields without making decisions."""
from __future__ import annotations
import gzip,json,re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; DATA=ROOT/'data/raw/open'; OUT=ROOT/'incubator/runs/inc093_v24_source_field_inventory'
FIELDS={
 'budget':('배정예산','추정가격','예정금액','사업예산','기초금액','용역금액','용 역 비','구매예정금액','예산액'),
 'contract_method':('계약방법','계 약 방 법','계약 방식','경쟁형태','입찰방법','협상에 의한 계약','수의계약','제한경쟁'),
 'region_restriction':('지역제한','지역 제한','주된 영업소','소재지','지역 업체','지역업체','입찰참가자격'),
 'industry_restriction':('업종제한','업종 제한','업종코드','입찰참가자격','등록한 업체','면허'),
}
def load():
 with gzip.open(DATA/'dev.jsonl.gz','rt',encoding='utf8') as h:return [json.loads(x) for x in h if x]
def candidates(text,terms):
 lines=text.splitlines();out=[]
 for i,line in enumerate(lines):
  if any(t in line for t in terms):
   lo=max(0,i-1);hi=min(len(lines),i+2);chunk='\n'.join(lines[lo:hi]).strip()
   if chunk and chunk not in out:out.append(chunk)
 return out
def main():
 OUT.mkdir(parents=True,exist_ok=True); rs=load(); records=[]; count={f:Counter() for f in FIELDS}
 for r in rs:
  source='\n'.join(d['text'] for d in r['docs']); row={'id':r['id'],'document_count':len(r['docs']),'fields':{f:candidates(source,t) for f,t in FIELDS.items()}}
  for f,x in row['fields'].items():count[f]['zero']+=not bool(x);count[f]['one']+=len(x)==1;count[f]['many']+=len(x)>1
  records.append(row)
 (OUT/'candidates.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in records)+'\n',encoding='utf8')
 report={'purpose':'exact source candidate inventory only; no source-meta consistency decision','field_terms':FIELDS,'count':{f:dict(c) for f,c in count.items()},'records':len(records),'source_sha256':__import__('hashlib').sha256((DATA/'dev.jsonl.gz').read_bytes()).hexdigest()}
 (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
