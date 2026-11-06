#!/usr/bin/env python3
"""Score INC-088 and INC-091 exactly on the frozen INC-085 cohort."""
from __future__ import annotations
import csv, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; ITEMS=tuple(f'v{i}' for i in range(1,25))
def rows(p):return [json.loads(x) for x in p.read_text(encoding='utf8').splitlines() if x]
def score(pred,gold,ids):
 out=[]
 for i in ITEMS:
  tp=fp=fn=0
  for rid in ids:
   v=pred[rid][i];y=int(gold[rid][i]);tp+=v==y==1;fp+=v==1 and y==0;fn+=v==0 and y==1
  out.append({'item':i,'tp':tp,'fp':fp,'fn':fn,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0})
 return sum(x['f1'] for x in out)/24,out
def main():
 ids=[x['id'] for x in rows(ROOT/'incubator/runs/inc085_fact_ledger_adjudication_dev64/manifest.jsonl')];gold={x['id']:x for x in csv.DictReader((ROOT/'data/raw/open/dev_labels.csv').open(encoding='utf8'))}
 high={x['id']:x['labels'] for x in rows(ROOT/'incubator/runs/inc088_openai_luna_high_full_dev_card/responses.jsonl')};op={x['id']:x['labels'] for x in rows(ROOT/'incubator/runs/inc091_luna_high_operational_dev64/responses.jsonl')}
 a,ai=score(high,gold,ids);b,bi=score(op,gold,ids); report={'cohort_size':len(ids),'high_baseline_macro_f1':a,'operational_macro_f1':b,'delta':b-a,'per_item':[{'item':x['item'],'high_f1':x['f1'],'operational_f1':y['f1'],'delta':y['f1']-x['f1']} for x,y in zip(ai,bi)]};p=ROOT/'incubator/runs/inc091_luna_high_operational_dev64/comparison_inc088_same_cohort.json';p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
