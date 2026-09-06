#!/usr/bin/env python3
"""No-LLM audit of v17 labels against observable restriction facts."""
from __future__ import annotations
import csv,gzip,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RAW=ROOT/'data/raw/open';OUT=ROOT/'incubator/runs/inc115_v17_policy_consistency_audit'
SME=re.compile(r'소기업|소상공인|중소기업')
def main():
 gold={x['id']:x for x in csv.DictReader((RAW/'dev_labels.csv').open(encoding='utf8'))};rows=[]
 with gzip.open(RAW/'dev.jsonl.gz','rt',encoding='utf8') as h:
  for line in h:
   r=json.loads(line);m=r['meta'];
   if m.get('업무구분')!='물품(내자)' or not m.get('입찰추정가격') or int(m['입찰추정가격'])>=100_000_000:continue
   text='\n'.join(d['text'] for d in r['docs']);hits=[]
   for x in SME.finditer(text):
    s=max(0,x.start()-120);e=min(len(text),x.end()+260);v=' '.join(text[s:e].split())
    if v not in hits:hits.append(v)
   rows.append({'id':r['id'],'v17':int(gold[r['id']]['v17']),'law':m.get('적용계약법'),'method':m.get('계약방법'),'price':m.get('입찰추정가격'),'clause':m.get('조항호내용'),'product':m.get('세부품명번호목록'),'sme_hit_count':len(hits),'sme_contexts':hits[:3]})
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'records.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n',encoding='utf8');report={'eligible_notice_count':len(rows),'v17_positive':sum(x['v17'] for x in rows),'positive_with_sme_text':sum(x['v17'] and x['sme_hit_count']>0 for x in rows),'negative_with_sme_text':sum(not x['v17'] and x['sme_hit_count']>0 for x in rows)};(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
