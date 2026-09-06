#!/usr/bin/env python3
"""All-dev law-RAG family passes with disjoint 24-item merge."""
from __future__ import annotations
import argparse, csv, fcntl, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from transformers import AutoTokenizer
import inc001_simple_joint24 as common
from inc007_token_admission_profile import count_messages
from inc006_input_budget_ablation import metric

FAMILIES = {"qualification_geo": ("v1","v2","v3","v4","v5","v6","v7","v8","v9"), "products": ("v10","v11","v12","v13","v14","v15","v16","v17","v18"), "procedure": ("v19","v21","v22","v23"), "sw_meta": ("v20","v24")}

def read_jsonl(p: Path) -> list[dict[str,Any]]: return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def append(p: Path, x: dict[str,Any]) -> None:
    with p.open("a",encoding="utf-8") as h: h.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n");h.flush()
def all_docs(r: dict[str,Any]) -> str:
    return "\n\n".join(f"[{d['type']}:{d['doc_id']}]\n{d['text']}" for d in sorted(r['docs'],key=lambda d:(common.DOCUMENT_ORDER[d['type']],d['doc_id'])))
def schema(items: tuple[str,...]) -> dict[str,Any]:
    return {"type":"object","additionalProperties":False,"required":list(items),"properties":{i:{"type":"object","additionalProperties":False,"required":["위반여부","근거문구"],"properties":{"위반여부":{"type":"integer","enum":[0,1]},"근거문구":{"type":["string","null"],"maxLength":500}}} for i in items}}
def card(family: str, items: tuple[str,...], table: dict[str,Any], retrieval: dict[str,Any], limit: int) -> str:
    parts=["[Organizer-law retrieved context: fixed legal context, never notice evidence]"]
    for item in items:
        result=retrieval[item]["results"][0]
        definition=table[item]
        parts += [f"[{item}] {definition['항목명']}; 국가={definition.get('국가계약법','')}; 지방={definition.get('지방계약법','')}; 비고={definition.get('비고','')}", f"[법령 원문:{result['source_file']}@{result['start']}]\n{result['text'][:limit]}"]
    return "\n\n".join(parts)
def messages(r:dict[str,Any], items:tuple[str,...], context:str) -> list[dict[str,str]]:
    lines=[]
    for i in items:
        d=i;lines.append(f"- {d}: 이 family의 해당 항목을 독립 판정")
    sys="\n".join(["당신은 공공입찰 법령위반을 판정한다. 제공된 전체 공고·메타와 fixed 법령원문을 사용해 아래 항목만 판정한다.","키워드만으로 1을 정하지 말고 법령 적용요건·예외·금액·문서 사실을 함께 확인한다.","non-absence에서 1이면 근거문구는 제공 문서의 변경 없는 연속 substring(500자 이하)이어야 한다. 법령 context는 evidence가 아니다. 0이면 null이다. 부재탐지(v10,v11,v16,v18,v20)는 근거문구 null이다.",*lines,"JSON 객체 하나만 출력한다. 각 항목은 {위반여부:0/1, 근거문구:string/null}이다."])
    user="\n\n".join([f"[공고 ID]\n{r['id']}","[나라장터 입력 메타]\n"+json.dumps(r['meta'],ensure_ascii=False,sort_keys=True),context,"[전체 문서]\n"+all_docs(r)])
    return [{"role":"system","content":sys},{"role":"user","content":user}]
def post(content:str, r:dict[str,Any], items:tuple[str,...]) -> tuple[dict[str,dict[str,Any]],list[str]]:
    payload=common.parse_json(content);source="\n".join(d['text'] for d in r['docs']);out={};w=[]
    for item in items:
        cell=payload.get(item)
        if not isinstance(cell,dict) or cell.get("위반여부") not in (0,1): raise ValueError(f"invalid {item}")
        v=int(cell['위반여부']);e=cell.get('근거문구')
        if item in common.ABSENCE_ITEMS:e=""
        elif v:
            e=e.strip() if isinstance(e,str) else ""
            if e not in source:w.append(f"{item}:invalid_evidence");v,e=0,""
            else:e=e[:500]
        else:e=""
        out[item]={"위반여부":v,"근거문구":e}
    return out,w
def main()->None:
    a=argparse.ArgumentParser();a.add_argument('--config',default='incubator/configs/inc021_rag_family_pass_dev200.json');a.add_argument('--mode',choices=('preflight','run'),default='preflight');z=a.parse_args();root=common.repo_root();cfg=json.loads((root/z.config).read_text());load_dotenv(root/'.env');out=root/'incubator/runs'/cfg['experiment_id'];out.mkdir(parents=True,exist_ok=True);lock=(out/'.run.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    data=root/cfg['data_root'];records={r['id']:r for r in common.read_jsonl_gz(data/'dev.jsonl.gz')};labels={r['id']:r for r in common.read_csv(data/'dev_labels.csv')};table=json.loads((data/'data/항목표.json').read_text())['항목'];index=json.loads((root/cfg['rag_index_path']).read_text());retrieval={r['item']:r for r in index['retrieval']};tok=AutoTokenizer.from_pretrained(cfg['model_tokenizer']);budget=cfg['max_model_len']-cfg['output_reserve_tokens'];cards={f:card(f,its,table,retrieval,cfg['law_excerpt_chars']) for f,its in FAMILIES.items()};prepared=[]
    for r in records.values():
      for family,its in FAMILIES.items():
        m=messages(r,its,cards[family]);n=count_messages(tok,m)
        if n>budget:raise RuntimeError(f"overflow {r['id']} {family} {n}>{budget}")
        prepared.append({"id":r['id'],"family":family,"items":its,"messages":m,"prompt_tokens":n,"prompt_sha256":common.sha256_text(json.dumps(m,ensure_ascii=False,sort_keys=True))})
    estimate=sum(x['prompt_tokens']*cfg['observed_input_cost_per_token_usd']+cfg['assumed_completion_tokens']*cfg['observed_completion_cost_per_token_usd'] for x in prepared);plan={"experiment_id":cfg['experiment_id'],"hypothesis":"retrieved organizer law plus disjoint legal-family attention improves global macro F1 over INC-018 single_full without document-pass OR inflation","cohort_count":len(records),"request_count":len(prepared),"family_request_counts":{f:len(records) for f in FAMILIES},"prompt_token_budget":budget,"prompt_token_max":max(x['prompt_tokens'] for x in prepared),"projected_cost_usd":estimate,"max_cost_usd":cfg['max_cost_usd'],"success_gate":"macro F1 > INC-018 single_full 0.19361 + 0.05; evidence validity >= 0.70; >=95% successful calls","rag_index_sha256":common.sha256_file(root/cfg['rag_index_path'])};common.write_json(out/'config.json',cfg);common.write_json(out/'plan.json',plan);common.write_jsonl(out/'inputs.jsonl',prepared)
    if estimate>cfg['max_cost_usd']:raise RuntimeError('cost ceiling');
    if z.mode=='preflight':print(json.dumps({'status':'preflight_ok',**plan},ensure_ascii=False,indent=2));return
    ck=out/'checkpoint.jsonl';done={(x['id'],x['family']):x for x in read_jsonl(ck)} if ck.exists() else {}
    def run(q):
      res={"raw_response":"","model":cfg['model'],"usage":{},"latency_seconds":0.,"finish_reason":None,"success":False}
      try:
       c=common.completion(cfg,q['messages'],schema(q['items']));res.update({"raw_response":c.content,"model":c.model,"usage":c.usage,"latency_seconds":c.latency_seconds,"finish_reason":c.finish_reason});j,w=post(c.content,records[q['id']],q['items']);res['success']=True
      except Exception as e:j={i:{"위반여부":0,"근거문구":""} for i in q['items']};w=[f"failure:{type(e).__name__}:{str(e)[:200]}"]
      return {"id":q['id'],"family":q['family'],"judgment":j,"response":res,"warnings":w}
    rem=[q for q in prepared if (q['id'],q['family']) not in done]
    with ThreadPoolExecutor(max_workers=cfg['concurrency']) as ex:
      fs=[ex.submit(run,q) for q in rem]
      for k,f in enumerate(as_completed(fs),1):
       x=f.result();done[(x['id'],x['family'])]=x;append(ck,x)
       if k%20==0 or k==len(rem):print(f'[{k}/{len(rem)}] completed',flush=True)
    rows=[]
    for rid in sorted(records):
      j=common.zero_judgment()
      for family in FAMILIES:j.update(done[(rid,family)]['judgment'])
      rows.append(common.to_row(rid,j))
    m,per=metric(rows,labels,records);metrics={"experiment_id":cfg['experiment_id'],"request_count":len(done),"successful_request_count":sum(x['response']['success'] for x in done.values()),"reported_cost_usd":sum(float(x['response']['usage'].get('cost',0)or 0) for x in done.values()),"metrics":m,"per_item":per};metrics['success_gate_pass']=m['macro_f1']>.24361 and (m['evidence_validity']or 0)>=.70 and metrics['successful_request_count']>=len(prepared)*.95
    with (out/'predictions.csv').open('w',encoding='utf-8',newline='') as h:w=csv.DictWriter(h,fieldnames=common.CSV_COLUMNS,lineterminator='\n');w.writeheader();w.writerows(rows)
    common.write_jsonl(out/'responses.jsonl',[{"id":x['id'],"family":x['family'],**x['response'],"warnings":x['warnings']} for x in done.values()]);common.write_json(out/'metrics.json',metrics);print(json.dumps({'status':'complete','metrics':metrics},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
