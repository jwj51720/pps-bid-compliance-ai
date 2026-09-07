#!/usr/bin/env python3
"""Audit deterministic exact-source recovery on INC-103 teacher records."""
from __future__ import annotations
import gzip,json
from collections import Counter
from pathlib import Path
from evidence_resolver import resolve_quote

ROOT=Path(__file__).resolve().parents[2];RAW=ROOT/'data/raw/open';RUN=ROOT/'incubator/runs/inc103_unlabeled_casebook_t1_pilot';OUT=ROOT/'incubator/runs/inc104_casebook_quote_resolution_audit'
def main() -> None:
 with gzip.open(RAW/'train_unlabeled.jsonl.gz','rt',encoding='utf8') as h:records={x['id']:x for x in (json.loads(y) for y in h if y)}
 rows=[]
 for line in (RUN/'responses.jsonl').read_text(encoding='utf8').splitlines():
  x=json.loads(line)
  if not x.get('success'):continue
  for item,cell in x['record']['items'].items():
   if not cell['v']:continue
   resolved,status=resolve_quote(cell['quote'],records[x['id']]['docs'])
   rows.append({'id':x['id'],'item':item,'original_quote_valid':cell['quote_valid'],'resolution':status,'resolved_evidence':resolved,'resolved_is_source_substring':bool(resolved and any(resolved in d['text'] for d in records[x['id']]['docs']))})
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'records.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n',encoding='utf8')
 report={'positive_quotes':len(rows),'resolution_counts':dict(Counter(x['resolution'] for x in rows)),'resolved_exact_source_rate':sum(x['resolved_is_source_substring'] for x in rows)/len(rows) if rows else 1}
 (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
