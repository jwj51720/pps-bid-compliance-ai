#!/usr/bin/env python3
"""Offline dev/unlabeled exact-template overlap audit; no predictions."""
from __future__ import annotations
import hashlib,json,re,unicodedata
from collections import defaultdict
from pathlib import Path
import inc001_simple_joint24 as common
ROOT=Path(__file__).resolve().parents[2]
def norm(s):return re.sub(r'\s+',' ',unicodedata.normalize('NFC',s)).strip()
def digest(s):return hashlib.sha256(norm(s).encode()).hexdigest()
def main():
 d=ROOT/'data/raw/open';out=ROOT/'incubator/runs/inc055_unlabeled_template_overlap_audit';out.mkdir(parents=True,exist_ok=True)
 dev=common.read_jsonl_gz(d/'dev.jsonl.gz');un=common.read_jsonl_gz(d/'train_unlabeled.jsonl.gz');labels={x['id']:x for x in common.read_csv(d/'dev_labels.csv')}
 docs=defaultdict(list); lines=defaultdict(set)
 for r in dev:
  for doc in r['docs']:
   docs[digest(doc['text'])].append(r['id'])
   for line in doc['text'].splitlines():
    if norm(line):lines[digest(line)].add(r['id'])
 exact=set();shared=defaultdict(set);un_exact=0;un_line=0
 for r in un:
  hit=False;line_hit=False
  for doc in r['docs']:
   if digest(doc['text']) in docs: exact.update(docs[digest(doc['text'])]);hit=True
   for line in doc['text'].splitlines():
    ids=lines.get(digest(line),set())
    if ids: shared[r['id']].update(ids);line_hit|=bool(ids)
  un_exact+=hit;un_line+=line_hit
 item={}
 for k in common.ITEMS:
  pos=[r['id'] for r in dev if labels[r['id']][k]=='1'];item[k]={'positive_count':len(pos),'positive_with_exact_unlabeled_doc_neighbor':sum(i in exact for i in pos),'positive_with_shared_unlabeled_line_neighbor':sum(any(i in ids for ids in shared.values()) for i in pos)}
 report={'experiment_id':'inc055_unlabeled_template_overlap_audit','dev_notice_count':len(dev),'unlabeled_notice_count':len(un),'unlabeled_with_exact_dev_document':un_exact,'unlabeled_with_any_dev_line':un_line,'dev_notices_with_exact_doc_neighbor':len(exact),'dev_notices_with_shared_line_neighbor':len({i for x in shared.values() for i in x}),'items':item,'source_sha256':{'dev':common.sha256_file(d/'dev.jsonl.gz'),'unlabeled':common.sha256_file(d/'train_unlabeled.jsonl.gz'),'labels':common.sha256_file(d/'dev_labels.csv')}}
 common.write_json(out/'report.json',report);common.write_jsonl(out/'shared_line_neighbors.jsonl',[{'unlabeled_id':k,'dev_ids':sorted(v)} for k,v in shared.items()]);print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
