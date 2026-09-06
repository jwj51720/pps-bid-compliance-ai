#!/usr/bin/env python3
"""INC-070: generate and independently audit source-grounded legal essence cards.

This is deliberately not a label experiment.  Each card is a concise Korean
review aid distilled only from the organizer item table and the complete legal
units already audited by INC-023.  A second, independent model call checks
every proposed statement against the supplied source units.  A card is usable
only when that audit accepts it; unresolved manual citations are disclosed,
never guessed from memory.
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import inc001_simple_joint24 as common
from inc023_article_context_audit import active_body


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "incubator/runs/inc070_legal_essence_card_audit"
LAW_DIR = ROOT / "data/raw/open/data/법령패키지/법령"


def request_config(max_tokens: int) -> dict[str, Any]:
    return {
        "model": "google/gemma-4-26b-a4b-it",
        "api_url": "https://openrouter.ai/api/v1/chat/completions",
        "api_key_env": "OPENROUTER_API_KEY",
        "temperature": 0.0,
        "seed": 20260905,
        # 512 is a semantic-output reserve: three short Korean statements plus
        # an audit explanation, not a score-selected size limit.
        "max_tokens": max_tokens,
        "timeout_seconds": 120,
        "request_retries": 1,
    }


def load_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    data = ROOT / "data/raw/open"
    table = json.loads((data / "data/항목표.json").read_text(encoding="utf-8"))["항목"]
    audit = json.loads((ROOT / "incubator/data/derived/inc023_article_context_audit.json").read_text(encoding="utf-8"))
    return table, audit


def item_sources(item: str, audit: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    resolved, unresolved = [], []
    for row in audit["records"]:
        if row["item"] != item:
            continue
        target = resolved if row["status"] == "resolved_unique_article" else unresolved
        target.append(row)
    return resolved, unresolved


def source_unit(row: dict[str, Any]) -> str:
    # INC-023 offsets and hashes are relative to the active statutory body,
    # excluding supplementary provisions.  Reuse that exact normalization.
    source = active_body((LAW_DIR / row["source_file"]).read_text(encoding="utf-8"))
    unit = source[row["start_offset"] : row["end_offset"]].strip()
    if common.sha256_text(unit) != row["unit_sha256"]:
        raise RuntimeError(f"source hash mismatch: {row['item']} {row['source_file']} {row['article']}")
    return unit


def source_packet(item: str, table: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    resolved, unresolved = item_sources(item, audit)
    units = []
    seen = set()
    for row in resolved:
        key = (row["source_file"], row["start_offset"], row["end_offset"])
        if key in seen:
            continue
        seen.add(key)
        units.append({
            "source_id": f"S{len(units) + 1}", "jurisdiction": row["jurisdiction"],
            "citation": row["citation"], "file": row["source_file"], "article": row["article"],
            "sha256": row["unit_sha256"], "text": source_unit(row),
        })
    return {
        "item": item,
        "item_definition": table[item],
        "resolved_complete_units": units,
        "unresolved_citations": [
            {key: row.get(key) for key in ("jurisdiction", "citation", "source_file", "article", "status")}
            for row in unresolved
        ],
    }


def card_schema() -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False,
            "required": ["applicability", "violation_rule", "exception_or_boundary", "source_ids"],
            "properties": {
                "applicability": {"type": "string"}, "violation_rule": {"type": "string"},
                "exception_or_boundary": {"type": "string"},
                "source_ids": {"type": "array", "items": {"type": "string"}},
            }}


def audit_schema() -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False,
            "required": ["accepted", "corrected_card", "reason"],
            "properties": {
                "accepted": {"type": "boolean"}, "corrected_card": card_schema(), "reason": {"type": "string"},
            }}


def generation_messages(packet: dict[str, Any]) -> list[dict[str, str]]:
    system = "\n".join([
        "당신은 공공조달 법령 검토 보조자다.",
        "오직 제공된 항목표와 법령 원문으로 해당 항목의 짧은 판단카드를 작성한다.",
        "각 문장은 법령에 없는 금액·요건·예외를 만들면 안 된다. 원문이 부족하거나 항목 자체가 대조형이면 그 한계를 명시한다.",
        "applicability에는 적용을 검토할 전제, violation_rule에는 v=1이 되는 법적/사실적 조건, exception_or_boundary에는 예외·비적용·원문상 미해결 경계를 쓴다.",
        "각 필드는 한국어 1~2문장으로 압축하되 숫자 제한 대신 의미 단위를 보존한다. source_ids에는 실제 사용한 S 번호만 넣는다.",
        "판정이나 공고문 근거를 만들지 말고 JSON 하나만 출력한다.",
    ])
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(packet, ensure_ascii=False)}]


def audit_messages(packet: dict[str, Any], candidate: dict[str, Any]) -> list[dict[str, str]]:
    system = "\n".join([
        "당신은 법령카드 감리자다. 제공된 원문만 사용해 후보 카드를 검증하고 필요하면 고친다.",
        "후보가 법령에 없는 요건·금액·예외를 단정하거나, 항목표의 한계를 숨기거나, source_ids가 틀리면 accepted=false로 하라.",
        "corrected_card는 accepted 여부와 무관하게 원문에만 근거한 가장 안전한 짧은 카드여야 한다.",
        "판정값이나 공고문 사실을 만들지 말고 JSON 하나만 출력한다.",
    ])
    user = {"source_packet": packet, "candidate_card": candidate}
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, ensure_ascii=False)}]


def call_generate(item: str, packet: dict[str, Any]) -> dict[str, Any]:
    path = OUT / "generated" / f"{item}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    response: Any = None
    try:
        response = common.completion(request_config(512), generation_messages(packet), card_schema())
        card = common.parse_json(response.content)
        entry = {"item": item, "success": True, "packet_sha256": common.sha256_text(json.dumps(packet, ensure_ascii=False, sort_keys=True)), "usage": response.usage, "raw_response": response.content, "card": card}
    except Exception as exc:
        entry = {"item": item, "success": False, "error": f"{type(exc).__name__}: {exc}", "usage": {} if response is None else response.usage, "raw_response": "" if response is None else response.content}
    path.parent.mkdir(parents=True, exist_ok=True); common.write_json(path, entry); return entry


def call_audit(item: str, packet: dict[str, Any], generated: dict[str, Any]) -> dict[str, Any]:
    path = OUT / "audited" / f"{item}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if not generated.get("success"):
        entry = {"item": item, "success": False, "error": "generation failed", "usage": {}, "raw_response": ""}
    else:
        response: Any = None
        try:
            response = common.completion(request_config(512), audit_messages(packet, generated["card"]), audit_schema())
            result = common.parse_json(response.content)
            entry = {"item": item, "success": True, "usage": response.usage, "raw_response": response.content, "audit": result}
        except Exception as exc:
            entry = {"item": item, "success": False, "error": f"{type(exc).__name__}: {exc}", "usage": {} if response is None else response.usage, "raw_response": "" if response is None else response.content}
    path.parent.mkdir(parents=True, exist_ok=True); common.write_json(path, entry); return entry


def preflight() -> None:
    table, audit = load_inputs(); packets = [source_packet(item, table, audit) for item in common.ITEMS]
    manifest = [{"item": p["item"], "complete_unit_count": len(p["resolved_complete_units"]), "unresolved_citation_count": len(p["unresolved_citations"]), "packet_sha256": common.sha256_text(json.dumps(p, ensure_ascii=False, sort_keys=True))} for p in packets]
    OUT.mkdir(parents=True, exist_ok=True); common.write_jsonl(OUT / "source_manifest.jsonl", manifest)
    common.write_json(OUT / "config.json", {"experiment_id": "inc070_legal_essence_card_audit", "model": request_config(512), "max_calls": 48, "max_cost_usd": 0.50, "policy": "all card statements must survive an independent source-only audit; unresolved citations are never synthesized"})
    print(json.dumps({"status": "preflight_ok", "items": len(packets), "calls": 48, "items_with_unresolved_citations": [m["item"] for m in manifest if m["unresolved_citation_count"]]}, ensure_ascii=False, indent=2))


def run(workers: int) -> None:
    table, audit = load_inputs(); packets = {item: source_packet(item, table, audit) for item in common.ITEMS}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(call_generate, item, packets[item]): item for item in common.ITEMS}
        for number, future in enumerate(as_completed(futures), 1):
            future.result(); print(f"generated={number}/24", flush=True)
    generated = {item: json.loads((OUT / "generated" / f"{item}.json").read_text(encoding="utf-8")) for item in common.ITEMS}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(call_audit, item, packets[item], generated[item]): item for item in common.ITEMS}
        for number, future in enumerate(as_completed(futures), 1):
            future.result(); print(f"audited={number}/24", flush=True)


def aggregate() -> None:
    table, audit = load_inputs(); cards, rows = {}, []
    for item in common.ITEMS:
        packet = source_packet(item, table, audit)
        generated = json.loads((OUT / "generated" / f"{item}.json").read_text(encoding="utf-8"))
        checked = json.loads((OUT / "audited" / f"{item}.json").read_text(encoding="utf-8"))
        accepted = bool(checked.get("success") and checked.get("audit", {}).get("accepted"))
        rows.append({"item": item, "generation_success": generated.get("success", False), "audit_success": checked.get("success", False), "accepted": accepted, "unresolved_citation_count": len(packet["unresolved_citations"]), "generation_cost": float(generated.get("usage", {}).get("cost", 0) or 0), "audit_cost": float(checked.get("usage", {}).get("cost", 0) or 0)})
        if accepted:
            cards[item] = {"item_definition": table[item], "card": checked["audit"]["corrected_card"], "source_units": [{key: unit[key] for key in ("source_id", "jurisdiction", "citation", "file", "article", "sha256")} for unit in packet["resolved_complete_units"]], "unresolved_citations": packet["unresolved_citations"]}
    artifact = {"card_version": "legal_essence_cards_v1", "purpose": "Short source-grounded legal review aids; not deterministic label rules and not evidence.", "source_audit": "inc023_article_context_audit", "cards": cards}
    common.write_json(ROOT / "incubator/data/derived/legal_essence_cards_v1.json", artifact)
    report = {"experiment_id": "inc070_legal_essence_card_audit", "accepted_count": len(cards), "rejected_or_failed_items": [r["item"] for r in rows if not r["accepted"]], "total_cost_usd": sum(r["generation_cost"] + r["audit_cost"] for r in rows), "per_item": rows, "promotion": "Only if all 24 cards pass source audit can INC-071 isolate cards versus no-card in full-notice judgment."}
    common.write_json(OUT / "report.json", report); print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--mode", required=True, choices=("preflight", "run", "aggregate")); parser.add_argument("--workers", type=int, default=12); args = parser.parse_args()
    load_dotenv(ROOT / ".env"); OUT.mkdir(parents=True, exist_ok=True)
    if args.mode == "preflight": preflight()
    elif args.mode == "run": run(args.workers)
    else: aggregate()


if __name__ == "__main__":
    main()
