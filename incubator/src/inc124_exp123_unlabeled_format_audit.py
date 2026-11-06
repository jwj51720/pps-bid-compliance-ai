#!/usr/bin/env python3
"""No-label, no-model format audit for the three frozen EXP-123 rules."""
from __future__ import annotations

import gzip
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "incubator/submission_candidates/exp123_card_v6_frozen_rules"))
from src.frozen_rules import apply_frozen_rules

ITEMS = ("v2", "v3", "v21")


def main() -> None:
    counts, maximum, invalid = Counter(), Counter(), []
    records = 0
    with gzip.open(ROOT / "data/raw/open/train_unlabeled.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line); records += 1
            blank = {item: {"위반여부": 0, "근거문구": ""} for item in ITEMS}
            judgment = apply_frozen_rules(record, blank)
            source = "\n".join(document["text"] for document in record["docs"])
            for item in ITEMS:
                if judgment[item]["위반여부"]:
                    evidence = judgment[item]["근거문구"]
                    counts[item] += 1; maximum[item] = max(maximum[item], len(evidence))
                    if not evidence or len(evidence) > 500 or evidence not in source:
                        invalid.append({"id": record["id"], "item": item, "evidence_chars": len(evidence)})
    result = {"experiment_id": "inc124_exp123_unlabeled_format_audit", "records": records, "positive_counts": dict(counts), "positive_rates": {item: counts[item] / records for item in ITEMS}, "max_evidence_chars": dict(maximum), "invalid_evidence": invalid[:20], "invalid_evidence_count": len(invalid), "interpretation": "format and activation audit only; unlabeled prevalence is not performance evidence"}
    output = ROOT / "incubator/runs/inc124_exp123_unlabeled_format_audit"; output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
