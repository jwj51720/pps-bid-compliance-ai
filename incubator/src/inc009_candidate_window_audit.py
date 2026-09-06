#!/usr/bin/env python3
"""Offline source-offset candidate-window audit; no labels inform cue creation."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common


# Derived only from the organizer item names/notes and competition description.
# Dev labels are read only after extraction, to evaluate coverage.
CUES: dict[str, tuple[str, ...]] = {
    "v1": (r"참가자격", r"입찰참가", r"자격.*(?:제한|요건)", r"(?:기관|업체).*(?:한정|제한)"),
    "v2": (r"(?:납품|수행|유사|공사).*실적", r"실적.*(?:이상|요건|제한)", r"최근\s*\d+년"),
    "v3": (r"실적", r"(?:추정|기초|사업).*금액", r"배\s*이상"),
    "v4": (r"특정.*(?:실적|기관|업체)", r"(?:납품|수행|유사).*실적", r"입찰참가자격"),
    "v5": (r"(?:지역|소재지|본사|영업소)", r"입찰참가자격", r"제한지역"),
    "v6": (r"(?:시|군|구).*(?:소재|본사|영업소)", r"지역제한", r"입찰참가자격"),
    "v7": (r"인접", r"연접", r"(?:시|군|구).*(?:소재|본사|영업소)"),
    "v8": (r"실적", r"(?:지역|소재지|본사|영업소)", r"입찰참가자격"),
    "v9": (r"모델명", r"제조사", r"규격", r"동등", r"이상"),
    "v10": (r"경쟁제품", r"직접생산", r"직접\s*생산", r"중소기업자간"),
    "v11": (r"경쟁제품", r"중소기업", r"중소기업자간"),
    "v12": (r"직접생산", r"직접\s*생산", r"일반제품", r"생산확인"),
    "v13": (r"경쟁제품", r"소기업", r"소상공인", r"중소기업자간"),
    "v14": (r"중소기업", r"중소기업자", r"중소기업제품"),
    "v15": (r"소기업", r"소상공인", r"판로지원", r"중소기업"),
    "v16": (r"중소기업", r"판로지원", r"입찰참가자격"),
    "v17": (r"중소기업", r"소기업", r"소상공인"),
    "v18": (r"소기업", r"소상공인", r"판로지원"),
    "v19": (r"물품공급", r"공급확약", r"확약서", r"제조사.*확약"),
    "v20": (r"소프트웨어", r"SW사업", r"소프트웨어사업자", r"입찰참가자격"),
    "v21": (r"공동수급", r"공동도급", r"분담", r"지분", r"%"),
    "v22": (r"현장설명", r"현장\s*설명", r"참석.*(?:자격|업체)", r"제안서"),
    "v23": (r"현장설명", r"현장\s*설명", r"공고기간", r"제안서"),
    "v24": (r"(?:추정가격|기초금액|사업예산|예정가격)", r"계약방법", r"지역제한", r"업종"),
}

# One offline repair: remove generic terms whose manual audit showed they were
# acting as all-notice selectors, not item-specific attention cues.
REFINED_CUES = dict(CUES)
REFINED_CUES.update({
    "v20": (r"소프트웨어", r"SW사업", r"소프트웨어사업자"),
    "v21": (r"공동수급", r"공동도급", r"분담", r"지분"),
    "v22": (r"현장설명", r"현장\s*설명", r"참석.*(?:자격|업체)"),
    "v23": (r"현장설명", r"현장\s*설명"),
})


def merged_windows(text: str, patterns: tuple[str, ...], radius: int, maximum: int) -> list[dict[str, Any]]:
    matches: list[tuple[int, int, str]] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            matches.append((max(0, match.start() - radius), min(len(text), match.end() + radius), pattern))
    matches.sort()
    merged: list[dict[str, Any]] = []
    for start, end, pattern in matches:
        if merged and start <= merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], end)
            merged[-1]["patterns"].append(pattern)
        else:
            merged.append({"start": start, "end": end, "patterns": [pattern]})
    result: list[dict[str, Any]] = []
    for window in merged:
        start, end = window["start"], window["end"]
        if end - start > maximum:
            end = start + maximum
        result.append({"start": start, "end": end, "patterns": sorted(set(window["patterns"])), "text": text[start:end]})
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="incubator/configs/inc009_candidate_window_audit.json")
    args = parser.parse_args()
    root = common.repo_root()
    config = json.loads((root / args.config).read_text(encoding="utf-8"))
    output = root / "incubator/runs" / config["experiment_id"]
    output.mkdir(parents=True, exist_ok=True)
    records = common.read_jsonl_gz(root / config["data_root"] / "dev.jsonl.gz")
    labels = {row["id"]: row for row in common.read_csv(root / config["data_root"] / "dev_labels.csv")}
    cues = REFINED_CUES if config.get("cue_profile") == "refined_procedure" else CUES
    manifest: list[dict[str, Any]] = []
    stats: dict[str, dict[str, Any]] = {item: {"gold_positive": 0, "positive_with_candidate": 0, "gold_negative": 0, "negative_with_candidate": 0, "candidate_notices": 0, "candidate_windows": 0, "window_doc_types": Counter()} for item in common.ITEMS}
    family_by_item = {item: family for family, items in config["families"].items() for item in items}
    for record in records:
        for item in common.ITEMS:
            windows: list[dict[str, Any]] = []
            for document in record["docs"]:
                for window in merged_windows(document["text"], cues[item], config["neighbor_chars"], config["max_window_chars"]):
                    windows.append({"doc_id": document["doc_id"], "doc_type": document["type"], **window})
            gold = labels[record["id"]][item] == "1"
            entry = stats[item]
            entry["gold_positive" if gold else "gold_negative"] += 1
            if windows:
                entry["positive_with_candidate" if gold else "negative_with_candidate"] += 1
                entry["candidate_notices"] += 1
                entry["candidate_windows"] += len(windows)
                entry["window_doc_types"].update(window["doc_type"] for window in windows)
            manifest.append({"id": record["id"], "item": item, "family": family_by_item[item], "candidate_count": len(windows), "windows": windows})
    item_report: list[dict[str, Any]] = []
    for item in common.ITEMS:
        entry = stats[item]
        item_report.append({"item": item, "family": family_by_item[item], "gold_positive": entry["gold_positive"], "candidate_recall": entry["positive_with_candidate"] / entry["gold_positive"] if entry["gold_positive"] else None, "gold_negative": entry["gold_negative"], "negative_candidate_rate": entry["negative_with_candidate"] / entry["gold_negative"] if entry["gold_negative"] else None, "mean_windows_per_candidate_notice": entry["candidate_windows"] / entry["candidate_notices"] if entry["candidate_notices"] else 0, "candidate_notices": entry["candidate_notices"], "document_types": dict(entry["window_doc_types"])})
    family_report: dict[str, Any] = {}
    for family, items in config["families"].items():
        entries = [row for row in item_report if row["item"] in items and row["gold_positive"]]
        family_report[family] = {"items_with_positives": len(entries), "minimum_item_candidate_recall": min(row["candidate_recall"] for row in entries) if entries else None, "mean_item_candidate_recall": sum(row["candidate_recall"] for row in entries) / len(entries) if entries else None, "max_mean_windows": max(row["mean_windows_per_candidate_notice"] for row in entries) if entries else 0}
    report = {"experiment_id": config["experiment_id"], "cue_profile": config.get("cue_profile", "baseline"), "method": "predeclared lexical/numeric cue windows over organizer source documents; labels used only after extraction", "source_sha256": {"dev": common.sha256_file(root / config["data_root"] / "dev.jsonl.gz"), "labels": common.sha256_file(root / config["data_root"] / "dev_labels.csv")}, "window_policy": {"neighbor_chars": config["neighbor_chars"], "max_window_chars": config["max_window_chars"]}, "family_report": family_report, "per_item": item_report}
    common.write_json(output / "config.json", config)
    common.write_jsonl(output / "candidate_manifest.jsonl", manifest)
    derived = root / "incubator/data/derived"
    derived.mkdir(parents=True, exist_ok=True)
    common.write_jsonl(derived / f"{config['experiment_id']}_candidate_manifest.jsonl", manifest)
    common.write_json(output / "report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
