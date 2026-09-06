#!/usr/bin/env python3
"""Describe metadata/source structure of true-positive vs false-negative absence cases."""
from __future__ import annotations
import csv,gzip,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];DATA=ROOT/'data/raw/open';RUN=ROOT/'incubator/runs/inc088_openai_luna_high_full_dev_card'; ITEMS=('v10','v11','v16','v18','v20')
def main():
 with gzip.open(DATA/'dev.jsonl.gz','rt',encoding='utf8') as h:rs=[json.loads(x) for x in h if x]
 gold={x['id']:x for x in csv.DictReader((DATA/'dev_labels.csv').open(encoding='utf8'))};pred={x['id']:x['labels'] for x in [json.loads(x) for x in (RUN/'responses.jsonl').read_text(encoding='utf8').splitlines() if x]}; fields=('업무구분','계약방법','낙찰방법','정보화사업여부','세부품명번호목록','조항호내용','지역제한여부','업종제한여부')
 cases=[]
 for r in rs:
  for item in ITEMS:
   if int(gold[r['id']][item]): cases.append({'id':r['id'],'item':item,'outcome':'TP' if pred[r['id']][item] else 'FN','meta':{f:r['meta'].get(f) for f in fields},'doc_types':[d['type'] for d in r['docs']],'chars':sum(len(d['text']) for d in r['docs']),'complete':r.get('input_completeness',{}).get('완전관측')})
 summary={}
 for item in ITEMS:
  xs=[x for x in cases if x['item']==item]
  for outcome in ('TP','FN'):
   ys=[x for x in xs if x['outcome']==outcome]; summary[f'{item}|{outcome}']={'count':len(ys),'meta_values':{f:dict(Counter(str(x['meta'][f]) for x in ys)) for f in fields},'doc_types':dict(Counter('+'.join(x['doc_types']) for x in ys)),'complete':dict(Counter(str(x['complete']) for x in ys))}
 out=ROOT/'incubator/runs/inc095_absence_positive_structure';out.mkdir(parents=True,exist_ok=True);(out/'cases.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in cases)+'\n',encoding='utf8');(out/'report.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
