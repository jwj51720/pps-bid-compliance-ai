#!/usr/bin/env python3
"""Build and audit a source-grounded v20 decision card without judging labels.

The card is deliberately a fact packet.  It preserves the organizer law's
threshold, amount definition, exceptions, and notice/RFP disclosure duty, but
does not turn lexical matches or metadata into a v20 prediction.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common


SW_CUE_RE = re.compile(
    r"소프트웨어(?:사업|산업|개발|구축|유지|운영)?|정보시스템|정보화(?:사업|시스템)?|"
    r"전자정부|디지털서비스|ICT|\bSW\b",
    re.IGNORECASE,
)
DISCLOSURE_CUE_RE = re.compile(
    r"대기업[^\n]{0,80}(?:참여[^\n]{0,40}제한|참여제한)|"
    r"(?:참여[^\n]{0,40}제한|참여제한)[^\n]{0,80}대기업|"
    r"사업금액의 하한|중소\s*소프트웨어|소프트웨어[^\n]{0,80}대기업",
    re.IGNORECASE,
)
EXCEPTION_CUE_RE = re.compile(r"예외사업|예외\s*인정|국방|외교|치안|전력|국가안보", re.IGNORECASE)


def line_excerpt(lines: list[str], line_numbers: list[int]) -> list[dict[str, Any]]:
    return [{"line": number, "text": lines[number - 1]} for number in line_numbers]


def spans_for(pattern: re.Pattern[str], document: dict[str, Any], cue_type: str) -> list[dict[str, Any]]:
    text = document["text"]
    spans = []
    for match in pattern.finditer(text):
        start = max(0, match.start() - 90)
        end = min(len(text), match.end() + 160)
        spans.append(
            {
                "cue_type": cue_type,
                "doc_id": document["doc_id"],
                "doc_type": document["type"],
                "start": start,
                "end": end,
                "matched_text": match.group(),
                "source_substring": text[start:end],
            }
        )
    return spans


def facts_for(record: dict[str, Any]) -> dict[str, Any]:
    cues: list[dict[str, Any]] = []
    for document in record["docs"]:
        cues.extend(spans_for(SW_CUE_RE, document, "sw_applicability"))
        cues.extend(spans_for(DISCLOSURE_CUE_RE, document, "required_disclosure_or_related"))
        cues.extend(spans_for(EXCEPTION_CUE_RE, document, "possible_exception"))
    meta = record["meta"]
    raw_information_project = meta.get("정보화사업여부")
    return {
        "id": record["id"],
        "metadata_facts": {
            "information_project_raw": raw_information_project,
            "estimated_price_raw": meta.get("입찰추정가격"),
            "budget_raw": meta.get("배정예산금액"),
        },
        "metadata_applicability_status": (
            "unknown" if raw_information_project in (None, "", "미입력") else "provided"
        ),
        "cue_counts": dict(Counter(cue["cue_type"] for cue in cues)),
        "cues": cues,
        "interpretation_guardrail": (
            "Cues are source locations for an LLM review, not an applicability finding, "
            "an exception finding, or a violation label."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="incubator/configs/inc013_v20_decision_card_audit.json")
    args = parser.parse_args()
    root = common.repo_root()
    config = json.loads((root / args.config).read_text(encoding="utf-8"))
    output = root / "incubator/runs" / config["experiment_id"]
    output.mkdir(parents=True, exist_ok=True)
    data_root = root / config["data_root"]
    law_path = data_root / config["law_path"]
    law_lines = law_path.read_text(encoding="utf-8").splitlines()
    records = common.read_jsonl_gz(data_root / "dev.jsonl.gz")
    labels = {row["id"]: row for row in common.read_csv(data_root / "dev_labels.csv")}
    facts = [facts_for(record) for record in records]
    positives = [fact for fact in facts if labels[fact["id"]][config["target_item"]] == "1"]
    negatives = [fact for fact in facts if labels[fact["id"]][config["target_item"]] == "0"]

    card = {
        "card_version": "v20_decision_card_v1",
        "item": "v20",
        "purpose": "Source-grounded review aid; it is not a deterministic classifier.",
        "source": {
            "relative_path": config["law_path"],
            "sha256": common.sha256_file(law_path),
            "law_title": law_lines[0],
        },
        "legal_facts_verbatim": {
            "threshold_rule": line_excerpt(law_lines, [11]),
            "non_software_split_exception": line_excerpt(law_lines, [12]),
            "amount_and_long_contract_rules": line_excerpt(law_lines, [16, 17, 18]),
            "notice_or_rfp_disclosure_duty": line_excerpt(law_lines, [19]),
            "appendix_1_thresholds": line_excerpt(law_lines, list(range(325, 337))),
            "exception_request_context": line_excerpt(law_lines, [22, 23, 24, 25, 26]),
        },
        "review_contract": [
            "First establish from the notice/RFP whether this is a software project; metadata marked 미입력 is unknown, not negative.",
            "Read the stated project amount under the law's amount definition; do not infer that budget and estimated price are interchangeable without source support.",
            "Check the notice/RFP for the required disclosure of whether the large-company participation threshold applies and its basis.",
            "Check source text for split-procurement, shared-performance, public-institution, or exception facts before deciding.",
            "Do not label v20 from a cue, amount, or missing metadata alone. v20 is absence-detection and its evidence must stay blank.",
        ],
        "document_cue_patterns": {
            "sw_applicability": SW_CUE_RE.pattern,
            "required_disclosure_or_related": DISCLOSURE_CUE_RE.pattern,
            "possible_exception": EXCEPTION_CUE_RE.pattern,
        },
    }

    def has(fact: dict[str, Any], cue: str) -> bool:
        return fact["cue_counts"].get(cue, 0) > 0

    report = {
        "experiment_id": config["experiment_id"],
        "method": config["policy"],
        "target_item": config["target_item"],
        "positive_count": len(positives),
        "negative_count": len(negatives),
        "gold_used_only_for_audit": True,
        "positive_sw_cue_coverage": sum(has(fact, "sw_applicability") for fact in positives) / len(positives),
        "negative_sw_cue_rate": sum(has(fact, "sw_applicability") for fact in negatives) / len(negatives),
        "positive_disclosure_cue_rate": sum(has(fact, "required_disclosure_or_related") for fact in positives) / len(positives),
        "negative_disclosure_cue_rate": sum(has(fact, "required_disclosure_or_related") for fact in negatives) / len(negatives),
        "positive_unknown_information_project_rate": sum(fact["metadata_applicability_status"] == "unknown" for fact in positives) / len(positives),
        "metadata_only_applicability_forbidden": True,
        "preflight_gate_pass": all(has(fact, "sw_applicability") for fact in positives),
        "source_sha256": {
            "dev": common.sha256_file(data_root / "dev.jsonl.gz"),
            "labels": common.sha256_file(data_root / "dev_labels.csv"),
            "law": common.sha256_file(law_path),
        },
    }
    common.write_json(output / "config.json", config)
    common.write_json(output / "report.json", report)
    common.write_jsonl(output / "notice_fact_manifest.jsonl", facts)
    common.write_json(root / "incubator/data/derived/v20_decision_card_v1.json", card)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
