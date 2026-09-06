#!/usr/bin/env python3
"""Compare direct high and clause-salient outputs; descriptive only."""
from __future__ import annotations
import csv,json
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; ITEMS=tuple(f'v{i}' for i in range(1,25))
def rows(p):return [json.loads(x) for x in p.read_text(encoding='utf8').splitlines() if x]
def main():
 gold={x['id']:x for x in csv.DictReader((ROOT/'data/raw/open/dev_labels.csv').open(encoding='utf8'))};a={x['id']:x['labels'] for x in rows(ROOT/'incubator/runs/inc088_openai_luna_high_full_dev_card/responses.jsonl')};b={x['id']:x['labels'] for x in rows(ROOT/'incubator/runs/inc096_luna_high_clause_salient_dev200/responses.jsonl')}; c=defaultdict(Counter)
 for rid in a:
  for i in ITEMS:
   if a[rid][i]!=b[rid][i]:c[i][f'{a[rid][i]}->{b[rid][i]}']+=1;c[i]['became_correct']+=int(b[rid][i]==int(gold[rid][i]));c[i]['became_wrong']+=int(a[rid][i]==int(gold[rid][i]))
 r={'run_a':'inc088 high baseline','run_b':'inc096 clause salient','changed_labels':sum(sum(x[k] for k in ('0->1','1->0')) for x in c.values()),'per_item':{i:dict(c[i]) for i in ITEMS}}
 p=ROOT/'incubator/runs/inc096_luna_high_clause_salient_dev200/comparison_inc088.json';p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(r,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
