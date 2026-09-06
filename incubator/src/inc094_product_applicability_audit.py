#!/usr/bin/env python3
"""Audit exact organizer product-index applicability against INC-088 errors."""
from __future__ import annotations
import csv,gzip,json,re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];DATA=ROOT/'data/raw/open'; IDX=ROOT/'incubator/data/derived/historical_exp014/competition_products_v1.json';RUN=ROOT/'incubator/runs/inc088_openai_luna_high_full_dev_card'
def main():
 products=json.loads(IDX.read_text(encoding='utf8'))['products'];
 with gzip.open(DATA/'dev.jsonl.gz','rt',encoding='utf8') as h:rs=[json.loads(x) for x in h if x]
 gold={x['id']:x for x in csv.DictReader((DATA/'dev_labels.csv').open(encoding='utf8'))};pred={x['id']:x['labels'] for x in [json.loads(x) for x in (RUN/'responses.jsonl').read_text(encoding='utf8').splitlines() if x]};out=[];summary=Counter()
 for r in rs:
  raw=str(r['meta'].get('세부품명번호목록') or '');codes=re.findall(r'\d{10}',raw);matches=[x for x in codes if x in products]; clause=str(r['meta'].get('조항호내용') or '');designated='지정 공고한 물품' in clause or '경쟁제품' in clause
  for item in ('v10','v11','v13'):
   y=int(gold[r['id']][item]);v=pred[r['id']][item];kind='FN' if y and not v else ('TP' if y and v else 'other');summary[(item,kind,'code_match')]+=bool(matches);summary[(item,kind,'clause_designated')]+=designated;summary[(item,kind,'count')]+=1
  out.append({'id':r['id'],'codes':codes,'matched_competition_codes':matches,'clause_designated_product':designated,'clause':clause})
 report={'source':'official competition-products exact-code CSV plus organizer metadata only','records':len(rs),'summary':{' | '.join(k):v for k,v in summary.items()},'interpretation':'Counts are descriptive only; no inference rule or threshold is selected.'}
 o=ROOT/'incubator/runs/inc094_product_applicability_audit';o.mkdir(parents=True,exist_ok=True);(o/'records.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in out)+'\n',encoding='utf8');(o/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
