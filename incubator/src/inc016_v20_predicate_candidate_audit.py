#!/usr/bin/env python3
"""Audit source locations for a decomposed v20 diagnostic, never labels."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from typing import Any

import inc001_simple_joint24 as common


# Applicability cues include explicit legal/software-business descriptions and
# technology terms. They intentionally over-retrieve: Gemma will adjudicate.
SW_RE = re.compile(
    r"소프트웨어\s*(?:사업자|사업|산업|진흥법|개발|구축|유지보수|운영)|"
    r"정보시스템(?:\s*(?:구축|운영|개발|관리))?|정보화\s*사업|전자정부법|"
    r"소프트웨어사업자\s*\(.*?서비스사업\)|\bS\s*/\s*W\b",
    re.IGNORECASE,
)
# A declaration candidate needs the legal participation-restriction concept,
# not a generic bid-participation sanction or an unrelated small-business term.
DECLARATION_RE = re.compile(
    r"소프트웨어진흥법\s*제?\s*48조|"
    r"소프트웨어사업자[^\n]{0,100}사업금액[^\n]{0,100}참여\s*제한|"
    r"사업금액(?:별)?\s*참여\s*제한|사업금액의\s*하한|"
    r"대기업(?:인)?\s*소프트웨어사업자[^\n]{0,100}참여|"
    r"대기업[^\n]{0,80}참여\s*제한[^\n]{0,80}(?:소프트웨어|사업금액)|"
    r"중소\s*소프트웨어사업자[^\n]{0,100}참여",
    re.IGNORECASE,
)


def locations(record: dict[str, Any], pattern: re.Pattern[str], kind: str) -> list[dict[str, Any]]:
    result = []
    for document in record["docs"]:
        for match in pattern.finditer(document["text"]):
            start, end = max(0, match.start() - 100), min(len(document["text"]), match.end() + 180)
            result.append({"predicate": kind, "doc_id": document["doc_id"], "doc_type": document["type"], "start": start, "end": end, "matched_text": match.group(), "source_substring": document["text"][start:end]})
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="incubator/configs/inc016_v20_predicate_candidate_audit.json")
    args = parser.parse_args()
    root = common.repo_root()
    config = json.loads((root / args.config).read_text(encoding="utf-8"))
    output = root / "incubator/runs" / config["experiment_id"]
    output.mkdir(parents=True, exist_ok=True)
    data = root / config["data_root"]
    labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    manifest = []
    summary: dict[str, Counter[str]] = {"positive": Counter(), "negative": Counter()}
    for record in common.read_jsonl_gz(data / "dev.jsonl.gz"):
        sw = locations(record, SW_RE, "sw_applicability_candidate")
        declaration = locations(record, DECLARATION_RE, "declaration_present_candidate")
        key = "positive" if labels[record["id"]][config["target_item"]] == "1" else "negative"
        summary[key]["records"] += 1
        summary[key]["sw"] += bool(sw)
        summary[key]["declaration"] += bool(declaration)
        summary[key]["sw_and_no_declaration"] += bool(sw) and not declaration
        manifest.append({"id": record["id"], "gold_used_only_for_audit": key == "positive", "sw_candidate_count": len(sw), "declaration_candidate_count": len(declaration), "candidates": [*sw, *declaration]})
    def rates(counter: Counter[str]) -> dict[str, float | int]:
        count = counter["records"]
        return {"count": count, **{name + "_rate": counter[name] / count for name in ("sw", "declaration", "sw_and_no_declaration")}}
    report = {
        "experiment_id": config["experiment_id"], "method": config["policy"], "candidate_patterns": {"sw_applicability": SW_RE.pattern, "declaration_present": DECLARATION_RE.pattern},
        "rates": {key: rates(value) for key, value in summary.items()},
        "source_sha256": {"dev": common.sha256_file(data / "dev.jsonl.gz"), "labels": common.sha256_file(data / "dev_labels.csv")},
    }
    common.write_json(output / "config.json", config)
    common.write_jsonl(output / "predicate_candidate_manifest.jsonl", manifest)
    common.write_json(output / "report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
