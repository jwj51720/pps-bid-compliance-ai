#!/usr/bin/env python3
"""Offline, conservative v24 source-to-metadata discrepancy candidate audit."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common


METHODS = {"일반경쟁": "일반경쟁", "제한경쟁": "제한경쟁", "수의계약": "수의계약", "협상에의한계약": "협상에의한계약", "협상에 의한 계약": "협상에의한계약", "규격가격동시입찰": "규격가격동시입찰"}
METHOD_RE = re.compile("|".join(map(re.escape, METHODS)))
MONEY_RE = re.compile(r"(?P<label>추정가격|기초금액|예정가격|사업예산|배정예산|총사업비)[^\n]{0,30}?(?P<amount>\d{1,3}(?:,\d{3})+|\d{5,})")
REGION_RE = re.compile(r"(?:지역제한|소재지|본사|영업소)[^\n]{0,120}")
INDUSTRY_RE = re.compile(r"(?:업종|면허)[^\n]{0,120}")


def normalized_method(value: Any) -> str | None:
    text = str(value or "")
    for raw, normalized in METHODS.items():
        if raw in text:
            return normalized
    return None


def audit_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    meta = record["meta"]
    meta_method = normalized_method(meta.get("계약방법"))
    candidates: list[dict[str, Any]] = []
    for document in record["docs"]:
        text = document["text"]
        for match in METHOD_RE.finditer(text):
            value = normalized_method(match.group())
            if meta_method and value and value != meta_method:
                candidates.append({"field": "contract_method", "doc_id": document["doc_id"], "doc_type": document["type"], "start": match.start(), "end": match.end(), "text": text[match.start():match.end()], "document_value": value, "metadata_value": meta_method})
        for match in MONEY_RE.finditer(text):
            amount = int(match.group("amount").replace(",", ""))
            label = match.group("label")
            expected = meta.get("입찰추정가격") if label == "추정가격" else meta.get("배정예산금액") if label in {"사업예산", "배정예산", "총사업비"} else None
            if expected is not None and amount != int(expected):
                candidates.append({"field": "money", "doc_id": document["doc_id"], "doc_type": document["type"], "start": match.start(), "end": match.end(), "text": text[match.start():match.end()], "document_value": amount, "metadata_value": int(expected), "money_label": label})
        if str(meta.get("지역제한여부") or "").upper() == "N":
            for match in REGION_RE.finditer(text):
                candidates.append({"field": "region_flag", "doc_id": document["doc_id"], "doc_type": document["type"], "start": match.start(), "end": match.end(), "text": text[match.start():match.end()], "document_value": "restriction_language", "metadata_value": "N"})
        if str(meta.get("업종제한여부") or "").upper() == "N":
            for match in INDUSTRY_RE.finditer(text):
                candidates.append({"field": "industry_flag", "doc_id": document["doc_id"], "doc_type": document["type"], "start": match.start(), "end": match.end(), "text": text[match.start():match.end()], "document_value": "restriction_language", "metadata_value": "N"})
    return candidates


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default="incubator/configs/inc011_v24_typed_audit.json"); args = parser.parse_args()
    root = common.repo_root(); config = json.loads((root / args.config).read_text(encoding="utf-8")); output = root / "incubator/runs" / config["experiment_id"]; output.mkdir(parents=True, exist_ok=True)
    records = common.read_jsonl_gz(root / config["data_root"] / "dev.jsonl.gz"); labels = {row["id"]: row for row in common.read_csv(root / config["data_root"] / "dev_labels.csv")}
    manifest, field_counts = [], {"positive": Counter(), "negative": Counter()}; positives = negatives = candidate_positives = candidate_negatives = 0
    for record in records:
        candidates = audit_record(record); gold = labels[record["id"]]["v24"] == "1"; positives += gold; negatives += not gold; candidate_positives += gold and bool(candidates); candidate_negatives += (not gold) and bool(candidates); field_counts["positive" if gold else "negative"].update(c["field"] for c in candidates)
        manifest.append({"id": record["id"], "gold_used_only_for_audit": gold, "candidate_count": len(candidates), "candidates": candidates})
    report = {"experiment_id": config["experiment_id"], "method": "conservative typed document-to-metadata discrepancy candidates; no automatic v24 label", "candidate_recall": candidate_positives / positives if positives else None, "negative_candidate_rate": candidate_negatives / negatives if negatives else None, "positive_count": positives, "negative_count": negatives, "field_candidate_counts": {key: dict(value) for key, value in field_counts.items()}, "source_sha256": {"dev": common.sha256_file(root / config["data_root"] / "dev.jsonl.gz"), "labels": common.sha256_file(root / config["data_root"] / "dev_labels.csv")}}
    common.write_json(output / "config.json", config); common.write_jsonl(output / "candidate_manifest.jsonl", manifest); common.write_json(output / "report.json", report); print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
