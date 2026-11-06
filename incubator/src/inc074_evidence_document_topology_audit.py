#!/usr/bin/env python3
"""Offline source-document topology audit; no predictions or API calls."""
from __future__ import annotations
import csv, gzip, json
from collections import Counter
from pathlib import Path
import inc001_simple_joint24 as common

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'incubator/runs/inc074_evidence_document_topology_audit'

def main():
 data=ROOT/'data/raw/open'
 with gzip.open(data/'dev.jsonl.gz','rt',encoding='utf-8') as f: records={r['id']:r for r in map(json.loads,f)}
 with (data/'dev_labels.csv').open(encoding='utf-8',newline='') as f: labels=list(csv.DictReader(f))
 report={'experiment_id':'inc074_evidence_document_topology_audit','method':'organizer gold-evidence exact-substring attribution; labels used only for audit, never prompt construction','items':{}}
 for item in common.ITEMS:
  n=int(item[1:]); positives=[r for r in labels if r[item]=='1']; types=Counter();empty=missing=0;examples={}
  for row in positives:
   evidence=row[f'e{n}']
   if not evidence: empty+=1;continue
   hit=[doc for doc in records[row['id']]['docs'] if evidence in doc['text']]
   if not hit:missing+=1;continue
   for doc in hit:
    types[doc['type']]+=1;examples.setdefault(doc['type'],row['id'])
  nonempty=len(positives)-empty
  report['items'][item]={'positive_count':len(positives),'nonempty_evidence_count':nonempty,'empty_evidence_count':empty,'unattributed_nonempty_count':missing,'evidence_document_types':dict(types),'single_document_complete':len(types)==1 and nonempty>0 and missing==0,'single_document_type':next(iter(types)) if len(types)==1 else None,'example_ids_by_document_type':examples}
 report['candidate_families']={
  'announcement_evidence_complete':['v2','v3','v7','v23'],
  'specification_evidence_complete':['v9'],
  'excluded_due_to_empty_or_multidoc':[x for x,v in report['items'].items() if not v['single_document_complete']],
 }
 OUT.mkdir(parents=True,exist_ok=True);common.write_json(OUT/'report.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
