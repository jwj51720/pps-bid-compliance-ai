#!/usr/bin/env python3
"""Offline provenance map for uniform legal-predicate discovery triage."""
from __future__ import annotations
import csv,json
from collections import Counter,defaultdict
from pathlib import Path
import inc001_simple_joint24 as common
ROOT=Path(__file__).resolve().parents[2]
def main():
 d=ROOT/'data/raw/open';out=ROOT/'incubator/runs/inc057_legal_predicate_feasibility_map';out.mkdir(parents=True,exist_ok=True)
 legal=json.loads((ROOT/'incubator/data/derived/inc023_article_context_audit.json').read_text())
 labels={r['id']:r for r in common.read_csv(d/'dev_labels.csv')};pred={r['id']:r for r in csv.DictReader((ROOT/'incubator/runs/inc041_v2_v3_v21_rule_composition_audit/dev_composed_predictions.csv').open(encoding='utf-8'))}
 records=common.read_jsonl_gz(d/'dev.jsonl.gz');items=[]
 for item in common.ITEMS:
  statuses=Counter(x['status'] for x in legal['records'] if x['item']==item);pos=[r['id'] for r in records if labels[r['id']][item]=='1'];e=f'e{item[1:]}'
  nonempty=[rid for rid in pos if labels[rid][e]];tp=fp=fn=0
  for rid in pred:
   g=int(labels[rid][item]);p=int(pred[rid][item]);tp+=g and p;fp+=not g and p;fn+=g and not p
  items.append({'item':item,'legal_units':dict(statuses),'positive_count':len(pos),'nonempty_organizer_evidence_count':len(nonempty),'organizer_evidence_observability':len(nonempty)/len(pos) if pos else None,'current_tp':tp,'current_fp':fp,'current_fn':fn,'current_f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.0})
 report={'experiment_id':'inc057_legal_predicate_feasibility_map','method':'joins pre-existing organizer-law unit resolution, organizer evidence availability, and fixed INC-041 diagnostic errors; no candidate predicate or prediction','items':items,'source_sha256':{'legal_map':common.sha256_file(ROOT/'incubator/data/derived/inc023_article_context_audit.json'),'labels':common.sha256_file(d/'dev_labels.csv'),'inc041_predictions':common.sha256_file(ROOT/'incubator/runs/inc041_v2_v3_v21_rule_composition_audit/dev_composed_predictions.csv')}}
 common.write_json(out/'report.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
