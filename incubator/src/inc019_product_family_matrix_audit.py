#!/usr/bin/env python3
"""Build auditable v10--v18 applicability facts without predicting labels."""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common


CODE_RE = re.compile(r"\d{10}")
CUES = {
    "direct_production": re.compile(r"직접\s*생산|직생"),
    "small_business": re.compile(r"소기업|소상공인"),
    "small_and_medium": re.compile(r"중소기업"),
    "competition_product": re.compile(r"중소기업자간\s*경쟁|경쟁제품"),
    "distribution_exception": re.compile(r"예외|판로지원"),
}


def products(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["세부품명번호"]: row["세부품명"] for row in csv.DictReader(handle) if CODE_RE.fullmatch(row.get("세부품명번호", ""))}


def cue_spans(record: dict[str, Any], pattern: re.Pattern[str], category: str) -> list[dict[str, Any]]:
    spans = []
    for document in record["docs"]:
        for match in pattern.finditer(document["text"]):
            start, end = max(0, match.start() - 80), min(len(document["text"]), match.end() + 180)
            spans.append({"category": category, "doc_id": document["doc_id"], "doc_type": document["type"], "start": start, "end": end, "matched_text": match.group(), "source_substring": document["text"][start:end]})
    return spans


def facts(record: dict[str, Any], index: dict[str, str]) -> dict[str, Any]:
    metadata_codes = sorted(set(CODE_RE.findall(str(record["meta"].get("세부품명번호목록") or ""))))
    document_codes = sorted({code for document in record["docs"] for code in CODE_RE.findall(document["text"])})
    all_codes = sorted(set(metadata_codes) | set(document_codes))
    matched = sorted(set(all_codes) & set(index))
    status = "matched" if matched else "not_matched" if all_codes else "unknown"
    cues = [span for category, pattern in CUES.items() for span in cue_spans(record, pattern, category)]
    return {
        "id": record["id"],
        "product_index_fact": {"status": status, "metadata_codes": metadata_codes, "document_codes": document_codes, "matched_codes": matched, "matched_product_names": [index[code] for code in matched]},
        "metadata_facts": {"estimated_price_raw": record["meta"].get("입찰추정가격"), "budget_raw": record["meta"].get("배정예산금액"), "contract_law_raw": record["meta"].get("적용계약법"), "business_type_raw": record["meta"].get("업무구분")},
        "cue_counts": dict(Counter(span["category"] for span in cues)), "cues": cues,
        "guardrail": "Exact product match and source cues are review facts only. They do not establish a v10--v18 violation, exception, or absence.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default="incubator/configs/inc019_product_family_matrix_audit.json"); args = parser.parse_args()
    root = common.repo_root(); config = json.loads((root / args.config).read_text(encoding="utf-8")); out = root / "incubator/runs" / config["experiment_id"]; out.mkdir(parents=True, exist_ok=True)
    data = root / config["data_root"]; index_path = data / config["product_csv_path"]; index = products(index_path); labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    manifest = [facts(record, index) for record in common.read_jsonl_gz(data / "dev.jsonl.gz")]
    report: dict[str, Any] = {"experiment_id": config["experiment_id"], "method": config["policy"], "record_count": len(manifest), "official_product_count": len(index), "items": {}}
    for item in config["items"]:
        groups: dict[str, Counter[str]] = {"positive": Counter(), "negative": Counter()}
        for row in manifest:
            group = "positive" if labels[row["id"]][item] == "1" else "negative"; fact = row["product_index_fact"]
            groups[group]["count"] += 1; groups[group][fact["status"]] += 1
            for cue in CUES: groups[group][f"cue_{cue}"] += bool(row["cue_counts"].get(cue, 0))
        report["items"][item] = {group: {key: value for key, value in values.items()} for group, values in groups.items()}
    report["source_sha256"] = {"dev": common.sha256_file(data / "dev.jsonl.gz"), "labels": common.sha256_file(data / "dev_labels.csv"), "product_csv": common.sha256_file(index_path)}
    common.write_json(out / "config.json", config); common.write_jsonl(out / "product_family_manifest.jsonl", manifest); common.write_json(out / "report.json", report)
    common.write_json(root / "incubator/data/derived/product_family_facts_v1.json", {"version": "product_family_facts_v1", "product_csv_sha256": report["source_sha256"]["product_csv"], "record_count": len(manifest), "records": manifest})
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
