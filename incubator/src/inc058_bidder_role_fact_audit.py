#!/usr/bin/env python3
"""Common bidder-eligibility role audit for v4/v7; no predictions."""
from __future__ import annotations
import json,re
from pathlib import Path
import inc001_simple_joint24 as common
ROOT=Path(__file__).resolve().parents[2]
ROLE=re.compile(r'입찰참가자격|입찰참가s*자격|입찰에s*참여|참가자격|참가할s*수|제한경쟁')
EVAL=re.compile(r'평가|점수|심사|제안서|수행능력')
INST=re.compile(r'국가기관|지방자치단체|공공기관|정부기관|발주기관|기관')
PERF=re.compile(r'실적|수행s*경험|경력')
REGION=re.compile(r'본점|주된\s*영업소|소재지|지역제한')
def main():
 d=ROOT/'data/raw/open';out=ROOT/'incubator/runs/inc058_bidder_role_fact_audit';out.mkdir(parents=True,exist_ok=True);rs=common.read_jsonl_gz(d/'dev.jsonl.gz');lab={x['id']:x for x in common.read_csv(d/'dev_labels.csv')};rows=[]
 for r in rs:
  facts={'v4':[],'v7':[]}
  for doc in r['docs']:
   for n,line in enumerate(doc['text'].splitlines()):
    if ROLE.search(line) and not EVAL.search(line):
     x={'doc_id':doc['doc_id'],'doc_type':doc['type'],'line_id':n,'source_line':line}
     if INST.search(line) and PERF.search(line):facts['v4'].append(x)
     if REGION.search(line):facts['v7'].append(x)
  rows.append({'id':r['id'],'facts':facts})
 by={x['id']:x for x in rows};report={'experiment_id':'inc058_bidder_role_fact_audit','method':'unchanged source lines require explicit bidder-eligibility role and exclude evaluation wording; v4 adds institution+performance, v7 adds region anchor; no predictions','items':{}}
 for item in ('v4','v7'):
  pos=[r['id'] for r in rs if lab[r['id']][item]=='1'];neg=[r['id'] for r in rs if lab[r['id']][item]=='0'];covered=[i for i in pos if by[i]['facts'][item]];active=[i for i in neg if by[i]['facts'][item]]
  report['items'][item]={'positive_count':len(pos),'candidate_recall':len(covered)/len(pos),'negative_activation':len(active)/len(neg),'uncovered_positive_ids':sorted(set(pos)-set(covered))}
 common.write_jsonl(out/'manifest.jsonl',rows);common.write_json(out/'report.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
