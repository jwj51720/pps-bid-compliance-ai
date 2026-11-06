#!/usr/bin/env python3
"""Paired Gemma test: EXP-120 card prompt versus compact official-law summary."""
from __future__ import annotations

import argparse, concurrent.futures, csv, fcntl, gzip, hashlib, json, os, sys, time
from collections import defaultdict
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "incubator/submission_candidates/exp120_card_v6"))
from src.data import load_decision_cards, load_item_table
from src.pipeline import parse_judgment, postprocess_judgment
from src.prompt import build_messages, build_system_prompt
from src.schema import ABSENCE_ITEMS, ITEMS, judgment_schema

CFG = ROOT / "incubator/configs/inc122_compact_legal_summary_pilot.json"
OUT = ROOT / "incubator/runs/inc122_compact_legal_summary_pilot"
RAW = ROOT / "data/raw/open"
CARDS = ROOT / "incubator/reference/dev_history/decision_cards_v6.json"
LEDGER = ROOT / "incubator/reference/dev_history/legal_condition_ledger_v1.json"
EXCLUSION_MANIFESTS = (ROOT / "incubator/data/derived/inc119_gemma_legal_transfer16_manifest.jsonl",)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rank(namespace: str, value: str) -> str:
    return hashlib.sha256(f"{namespace}:{value}".encode()).hexdigest()


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append(path: Path, value: Any) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n"); handle.flush(); os.fsync(handle.fileno())


def profile(record: dict[str, Any]) -> str:
    meta = record["meta"]
    if meta.get("적용계약법") == "국가계약법": return "national"
    if meta.get("계약방법") == "수의계약": return "local_small"
    if meta.get("낙찰방법") == "협상에의한계약": return "local_negotiated"
    return "local_general"


def records_and_labels() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]]]:
    with gzip.open(RAW / "dev.jsonl.gz", "rt", encoding="utf-8") as handle:
        records = {row["id"]: row for row in (json.loads(line) for line in handle if line.strip())}
    with (RAW / "dev_labels.csv").open(encoding="utf-8", newline="") as handle:
        labels = {row["id"]: row for row in csv.DictReader(handle)}
    return records, labels


def excluded_ids() -> set[str]:
    result = set()
    for path in EXCLUSION_MANIFESTS:
        result.update(json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines() if line)
    path = ROOT / "incubator/runs/inc121_output_contract_anchor_pilot/checkpoint.jsonl"
    result.update(json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines() if line)
    return result


def cohort(records: dict[str, dict[str, Any]], count: int) -> list[dict[str, str]]:
    excluded = excluded_ids(); groups: dict[str, list[str]] = defaultdict(list)
    for record_id, record in records.items():
        if record_id not in excluded: groups[profile(record)].append(record_id)
    rows = []
    for group in sorted(("national", "local_general", "local_small", "local_negotiated")):
        picks = sorted(groups[group], key=lambda value: rank(f"inc122-compact-law:{group}", value))[:count]
        if len(picks) != count: raise RuntimeError(f"insufficient profile {group}")
        rows += [{"id": value, "profile": group, "selection": "label-blind profile SHA rank after frozen exclusions"} for value in picks]
    return rows


def legal_summary(ledger: dict[str, Any], active_profile: str) -> str:
    entries = [entry for key, entry in ledger["entries"].items() if key.startswith(active_profile + "/")]
    lines = []
    for entry in sorted(entries, key=lambda value: value["group"]):
        for item in entry["items"]:
            suffix = f" 비적용 사유: {item['inactive_reason']}" if item.get("inactive_reason") else ""
            lines.append(f"[{item['item']}] {item['model_summary']}{suffix}")
    if set(line[1:line.index("]")] for line in lines) != set(ITEMS): raise RuntimeError("legal summary item coverage mismatch")
    return "[공식 법령 원문 기반 적용조건·예외 요약]\n아래는 제공된 공식 법령 자료의 적용조건과 예외를 짧게 정리한 참고자료다. 공고 원문과 메타에 적용하되, 근거문구에는 절대로 쓰지 말고 공고 원문만 인용한다.\n" + "\n".join(lines)


def request(config: dict[str, Any], messages: list[dict[str, str]]) -> dict[str, Any]:
    payload = {"model": config["model"], "messages": messages, "temperature": config["temperature"], "seed": config["seed"], "max_tokens": config["max_tokens"], "stream": False, "provider": {"require_parameters": True, "sort": "throughput"}, "response_format": {"type": "json_schema", "json_schema": {"name": "inc122_judgment", "strict": True, "schema": judgment_schema()}}}
    errors = []
    for attempt in range(config["request_retries"] + 1):
        started = time.monotonic()
        try:
            response = requests.post(config["api_url"], headers={"Authorization": f"Bearer {os.environ[config['api_key_env']]}", "Content-Type": "application/json"}, json=payload, timeout=config["timeout_seconds"])
            body = response.json()
            if response.ok:
                content = body["choices"][0]["message"]["content"]
                return {"success": True, "raw_response": content, "judgment": parse_judgment(content), "usage": body.get("usage", {}), "model": body.get("model", config["model"]), "latency_seconds": round(time.monotonic()-started, 3)}
            errors.append(f"HTTP {response.status_code}: {str(body)[:200]}")
            if response.status_code not in {408,409,429,500,502,503,504}: break
        except (requests.RequestException, ValueError, KeyError, IndexError, json.JSONDecodeError) as exc: errors.append(f"{type(exc).__name__}: {exc}")
        if attempt < config["request_retries"]: time.sleep(2**attempt)
    return {"success": False, "error": " | ".join(errors), "usage": {}, "raw_response": "", "latency_seconds": 0.0, "model": config["model"]}


def score(rows: dict[str, dict[str, Any]], labels: dict[str, dict[str, str]], ids: list[str]) -> dict[str, Any]:
    per, new_absence_fp = [], 0
    for item in ITEMS:
        tp=fp=fn=0
        for record_id in ids:
            gold, value = int(labels[record_id][item]), int(rows[record_id]["labels"][item]); tp += gold == value == 1; fp += gold == 0 and value == 1; fn += gold == 1 and value == 0
        if item in ABSENCE_ITEMS: new_absence_fp += fp
        precision=tp/(tp+fp) if tp+fp else 0.; recall=tp/(tp+fn) if tp+fn else 0.
        per.append({"item":item,"tp":tp,"fp":fp,"fn":fn,"precision":precision,"recall":recall,"f1":2*precision*recall/(precision+recall) if precision+recall else 0.})
    return {"macro_f1":sum(x["f1"] for x in per)/24,"recall_micro":sum(x["tp"] for x in per)/max(1,sum(x["tp"]+x["fn"] for x in per)),"absence_false_positives":new_absence_fp,"per_item":per}


def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",required=True,choices=("preflight","mock","run","aggregate")); args=ap.parse_args()
    config=json.loads(CFG.read_text(encoding="utf-8")); records,labels=records_and_labels(); table=load_item_table(RAW/"data/항목표.json"); cards=load_decision_cards(CARDS,table); ledger=json.loads(LEDGER.read_text(encoding="utf-8")); manifest=cohort(records,int(config["cohort_per_profile"])); ids=[row["id"] for row in manifest]
    base=build_system_prompt(table,decision_cards=cards); prepared=[]
    for row in manifest:
        record=records[row["id"]]
        for arm in config["arms"]:
            system=base if arm=="card_v6" else base+"\n\n"+legal_summary(ledger,row["profile"])
            messages=build_messages(record,system,int(config["context_chars"]))
            prepared.append({"id":row["id"],"profile":row["profile"],"arm":arm,"messages":messages,"prompt_sha256":hashlib.sha256(json.dumps(messages,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),"message_characters":sum(len(x["content"]) for x in messages)})
    pre={"experiment_id":config["experiment_id"],"config":config,"ids_sha256":hashlib.sha256("\n".join(ids).encode()).hexdigest(),"source_sha256":{"dev":digest(RAW/"dev.jsonl.gz"),"labels":digest(RAW/"dev_labels.csv"),"cards":digest(CARDS),"ledger":digest(LEDGER)},"requests":len(prepared),"summary_chars":{p:len(legal_summary(ledger,p)) for p in ledger["profiles"]},"prompt_characters":{a:max(x["message_characters"] for x in prepared if x["arm"]==a) for a in config["arms"]}}
    OUT.mkdir(parents=True,exist_ok=True); write(OUT/"config.json",config);write(OUT/"preflight.json",pre);(OUT/"cohort.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in manifest),encoding="utf-8")
    if pre["requests"]>config["max_requests"]: raise RuntimeError("request ceiling")
    if args.mode=="preflight": print(json.dumps({"status":"preflight_ok",**pre},ensure_ascii=False,indent=2));return
    if args.mode=="mock":
        for entry in prepared: postprocess_judgment({item:{"위반여부":0,"근거문구":None} for item in ITEMS},records[entry["id"]])
        print(json.dumps({"status":"mock_ok","requests":len(prepared)},ensure_ascii=False));return
    checkpoint=OUT/"checkpoint.jsonl"; done={}
    if checkpoint.exists():
        for line in checkpoint.read_text(encoding="utf-8").splitlines():
            row=json.loads(line);done[(row["id"],row["arm"])]=row
    if args.mode=="run":
        load_dotenv(ROOT/".env");
        if not os.environ.get(config["api_key_env"]): raise RuntimeError("missing API key")
        lock=(OUT/".active.lock").open("w");
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc: raise SystemExit("INC-122 already running") from exc
        pending=[x for x in prepared if (x["id"],x["arm"]) not in done]
        def work(entry):
            try:
                result=request(config,entry["messages"])
                result.update({"id":entry["id"],"arm":entry["arm"],"profile":entry["profile"]})
                if result["success"]:
                    processed=postprocess_judgment(result.pop("judgment"),records[entry["id"]])
                    result["labels"]={item:processed[item]["위반여부"] for item in ITEMS}
                    result["evidence"]={item:processed[item]["근거문구"] for item in ITEMS}
            except Exception as exc:
                result={"id":entry["id"],"arm":entry["arm"],"profile":entry["profile"],"success":False,"error":f"postprocess:{type(exc).__name__}: {exc}","usage":{},"raw_response":"","latency_seconds":0.0,"model":config["model"]}
            return result
        with concurrent.futures.ThreadPoolExecutor(max_workers=config["max_workers"]) as ex:
            fs={ex.submit(work,x):x for x in pending}
            for n,f in enumerate(concurrent.futures.as_completed(fs),1):
                row=f.result();append(checkpoint,row);print(f"completed={n}/{len(pending)} {row['id']}/{row['arm']} success={row['success']}",flush=True)
        return
    report={"experiment_id":config["experiment_id"],"cohort_size":len(ids),"arms":{}}
    for arm in config["arms"]:
        rows=[done.get((record_id,arm)) for record_id in ids];bad=[x for x in rows if not x or not x["success"]];value={x["id"]:x for x in rows if x and x["success"]};report["arms"][arm]={"success":len(value),"failures":len(bad),"reported_cost_usd":sum(float((x or {}).get("usage",{}).get("cost",0)or 0) for x in rows)}
        if not bad: report["arms"][arm].update(score(value,labels,ids))
    a,b=report["arms"]["card_v6"],report["arms"]["compact_legal_summary"]
    if "macro_f1" in a and "macro_f1" in b: report["delta"]={"macro_f1":b["macro_f1"]-a["macro_f1"],"recall_micro":b["recall_micro"]-a["recall_micro"],"absence_fp":b["absence_false_positives"]-a["absence_false_positives"]}
    write(OUT/"metrics.json",report);print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
