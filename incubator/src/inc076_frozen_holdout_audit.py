#!/usr/bin/env python3
"""Create a deterministic multi-label holdout and audit immutable INC-041."""
from __future__ import annotations
import csv, hashlib, json
from pathlib import Path
import inc001_simple_joint24 as common

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'incubator/runs/inc076_frozen_holdout_audit'
def f1(tp,fp,fn):return 2*tp/(2*tp+fp+fn)if 2*tp+fp+fn else 0
def main():
 data=ROOT/'data/raw/open';labels={r['id']:r for r in common.read_csv(data/'dev_labels.csv')}; ids=sorted(labels)
 # Deterministic greedy balancing: rare-label coverage is prioritized, then
 # total positive load.  IDs/hashes are the only tie breakers; no predictions.
 folds=[set(),set()];counts=[{x:0 for x in common.ITEMS}for _ in range(2)]
 ordered=sorted(ids,key=lambda rid:(-sum(labels[rid][x]=='1'for x in common.ITEMS),hashlib.sha256(f'inc076:{rid}'.encode()).hexdigest()))
 for rid in ordered:
  pos=[x for x in common.ITEMS if labels[rid][x]=='1']
  score=[]
  # Equal fold cardinality is a hard invariant.  Within the still-eligible
  # 100-row folds, distribute multi-label positive load as evenly as possible.
  for k in range(2):
   score.append((len(folds[k]) >= len(ids)//2, sum(counts[k][x]for x in pos), sum(counts[k].values()), len(folds[k]), k))
  k=min(score)[-1];folds[k].add(rid)
  for x in pos:counts[k][x]+=1
 pred={r['id']:r for r in csv.DictReader((ROOT/'incubator/runs/inc041_v2_v3_v21_rule_composition_audit/dev_composed_predictions.csv').open(encoding='utf-8'))}
 report={'experiment_id':'inc076_frozen_holdout_audit','split_policy':'deterministic multi-label positive-load balancing; labels select split only, never prompts/rules','folds':{}}
 for k,idsk in enumerate(folds):
  rows=[]
  for x in common.ITEMS:
   tp=fp=fn=0
   for rid in idsk:
    g=int(labels[rid][x]);p=int(pred[rid][x]);tp+=g and p;fp+=not g and p;fn+=g and not p
   rows.append({'item':x,'positive_count':sum(labels[rid][x]=='1'for rid in idsk),'tp':tp,'fp':fp,'fn':fn,'f1':f1(tp,fp,fn)})
  report['folds'][f'fold_{k}']={'size':len(idsk),'id_sha256':common.sha256_text('\n'.join(sorted(idsk))),'macro_f1':sum(r['f1']for r in rows)/24,'per_item':rows,'ids':sorted(idsk)}
 OUT.mkdir(parents=True,exist_ok=True);common.write_json(OUT/'holdout.json',report);print(json.dumps({'folds':{k:{'size':v['size'],'macro_f1':v['macro_f1']}for k,v in report['folds'].items()}},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
