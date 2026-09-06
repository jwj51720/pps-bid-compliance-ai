#!/usr/bin/env python3
"""Offline v24 audit using heading/value layout relations only."""
from __future__ import annotations
import csv, gzip, json, re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
METHODS = ("일반경쟁", "제한경쟁", "수의계약", "협상에 의한 계약", "협상에의한계약", "규격가격동시입찰")
FIELD = re.compile(r"(?P<label>계약방법|계약방식|추정가격|사업예산|배정예산|기초금액)\s*(?:[:|]|은|는)\s*(?P<value>[^\n|]{1,80})")

def method(value: str) -> str | None:
    return next((x.replace(" ", "") for x in METHODS if x in value), None)

def extract(record: dict[str, Any]) -> list[dict[str, Any]]:
    meta=record['meta']; out=[]
    for doc in record['docs']:
        for m in FIELD.finditer(doc['text']):
            label,value=m['label'],m['value']; field=None; conflict=False
            if label in ('계약방법','계약방식'):
                dv, mv=method(value),method(str(meta.get('계약방법') or ''))
                field='contract_method'; conflict=bool(dv and mv and dv!=mv)
            elif label=='추정가격':
                nums=re.findall(r'\d{1,3}(?:,\d{3})+|\d{5,}',value); field='estimated_price'; conflict=bool(nums and meta.get('입찰추정가격') is not None and int(nums[0].replace(',',''))!=int(meta['입찰추정가격']))
            else:
                nums=re.findall(r'\d{1,3}(?:,\d{3})+|\d{5,}',value); field='budget'; conflict=bool(nums and meta.get('배정예산금액') is not None and int(nums[0].replace(',',''))!=int(meta['배정예산금액']))
            if conflict: out.append({'field':field,'doc_id':doc['doc_id'],'doc_type':doc['type'],'start':m.start(),'end':m.end(),'text':m.group()})
    return out

def main() -> None:
    out=ROOT/'incubator/runs/inc011r_v24_layout_audit'; out.mkdir(parents=True,exist_ok=True)
    with gzip.open(ROOT/'data/raw/open/dev.jsonl.gz','rt',encoding='utf-8') as f: records=[json.loads(x) for x in f]
    labels={r['id']:r for r in csv.DictReader(open(ROOT/'data/raw/open/dev_labels.csv',encoding='utf-8'))}
    rows=[]; pos=neg=cp=cn=0; fields={'positive':Counter(),'negative':Counter()}
    for r in records:
        c=extract(r); gold=labels[r['id']]['v24']=='1'; pos+=gold; neg+=not gold; cp+=gold and bool(c); cn+=(not gold) and bool(c); fields['positive' if gold else 'negative'].update(x['field'] for x in c); rows.append({'id':r['id'],'gold_used_only_for_audit':gold,'candidate_count':len(c),'candidates':c})
    report={'experiment_id':'inc011r_v24_layout_audit','method':'heading/value-only typed comparison; no auto-label','positive_count':pos,'negative_count':neg,'candidate_recall':cp/pos,'negative_candidate_rate':cn/neg,'field_candidate_counts':{k:dict(v) for k,v in fields.items()}}
    (out/'candidate_manifest.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8'); (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
