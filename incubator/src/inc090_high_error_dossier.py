#!/usr/bin/env python3
"""Build an input-only diagnostic dossier for INC-088 errors (no model calls)."""
from __future__ import annotations
import csv, gzip, hashlib, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]; DATA=ROOT/'data/raw/open'; RUN=ROOT/'incubator/runs/inc088_openai_luna_high_full_dev_card'; ITEMS=tuple(f'v{i}' for i in range(1,25)); ABSENCE={'v10','v11','v16','v18','v20'}
def jl(p:Path): return [json.loads(x) for x in p.read_text(encoding='utf8').splitlines() if x]
def gz(p:Path):
 with gzip.open(p,'rt',encoding='utf8') as h:return [json.loads(x) for x in h if x]
def main():
 rec={x['id']:x for x in gz(DATA/'dev.jsonl.gz')}; gold={x['id']:x for x in csv.DictReader((DATA/'dev_labels.csv').open(encoding='utf8'))}; pred={x['id']:x['labels'] for x in jl(RUN/'responses.jsonl')}; cards=json.loads((ROOT/'incubator/reference/dev_history/decision_cards_v6.json').read_text(encoding='utf8'))['cards']
 errs=[]; stats=defaultdict(Counter)
 for rid,ps in pred.items():
  r=rec[rid]
  for item in ITEMS:
   y=int(gold[rid][item]);v=ps[item]
   if y==v:continue
   typ='FP' if v else 'FN'; mode='absence_condition' if item in ABSENCE else ('meta_document_consistency' if item=='v24' else 'positive_source_fact')
   e={'id':rid,'item':item,'item_name':cards[item]['item_name'],'error_type':typ,'diagnostic_mode':mode,'teacher_label':v,'gold_label':y,'meta':r['meta'],'document_types':[d['type'] for d in r['docs']],'source_characters':sum(len(d['text']) for d in r['docs']),'dropped_doc_counts':r.get('dropped_doc_counts',{}),'input_completeness':r.get('input_completeness',{}),'rank':hashlib.sha256(f'inc090:{item}:{typ}:{rid}'.encode()).hexdigest()}
   errs.append(e);stats[(item,typ,mode)]['count']+=1;stats[(item,typ,mode)][f'docs_{len(r["docs"])}']+=1;stats[(item,typ,mode)]['with_dropped_docs']+=int(bool(r.get('dropped_doc_counts')))
 groups=defaultdict(list)
 for e in errs:groups[(e['item'],e['error_type'])].append(e)
 sample=[]
 for k,xs in sorted(groups.items()):sample+=sorted(xs,key=lambda x:x['rank'])[:3]
 out=RUN/'high_error_dossier';out.mkdir(exist_ok=True)
 for e in sample:
  r=rec[e['id']];(out/f'{e["item"]}_{e["error_type"]}_{e["id"]}.json').write_text(json.dumps({'error':e,'legal_card':cards[e['item']], 'documents':r['docs']},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 report={'experiment':'inc090_high_error_dossier','source_run':'inc088_openai_luna_high_full_dev_card','model_calls':0,'total_errors':len(errs),'diagnostic_interpretation':{'positive_source_fact':'FN means a label-positive fact/condition must be recoverable from source/meta; inspect whether it is explicit versus compositional. FP needs source check because no model rationale was captured.','absence_condition':'positive may be supported by absence only after applicability, not by a literal positive phrase.','meta_document_consistency':'requires comparing source and metadata values, not ordinary keyword retrieval.'},'per_group':{' | '.join(k):dict(v) for k,v in stats.items()},'dossier_examples':len(sample),'sampling':'up to three stable hash-ranked records per item x FP/FN; selected after prediction only for analysis, never inference tuning'}
 (RUN/'high_error_atlas.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in errs)+'\n',encoding='utf8');(RUN/'high_error_dossier_summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
