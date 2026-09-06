#!/usr/bin/env python3
"""Global source-fragment coverage audit; no model calls or predictions."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common


ROOT = Path(__file__).resolve().parents[2]
SPLIT = re.compile(r"(?<=[.!?。])|(?<=[|])|(?=[•○●▪])")


def fragments(record: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    docs = sorted(record["docs"], key=lambda doc: (common.DOCUMENT_ORDER[doc["type"]], doc["doc_id"]))
    for doc_index, document in enumerate(docs, 1):
        offset = 0
        for line_index, raw_line in enumerate(document["text"].splitlines(keepends=True)):
            line = raw_line.rstrip("\r\n")
            if line:
                base = {"doc_id": document["doc_id"], "doc_type": document["type"], "line_id": f"L{doc_index}-{line_index}", "start": offset, "end": offset + len(line), "text": line, "kind": "line", "selectable": len(line) <= 500}
                result.append(base)
                cursor = 0
                for sentence_index, part in enumerate(SPLIT.split(line)):
                    if not part:
                        continue
                    start = line.find(part, cursor); cursor = start + len(part)
                    if part.strip(): result.append({**base, "fragment_id": f"S{doc_index}-{line_index}-{sentence_index}", "start": offset + start, "end": offset + start + len(part), "text": part, "kind": "sentence", "selectable": len(part) <= 500})
            offset += len(raw_line)
    return result


def main() -> None:
    data = ROOT / "data/raw/open"; output = ROOT / "incubator/runs/inc048_source_fragment_ontology_audit"; output.mkdir(parents=True, exist_ok=True)
    records = common.read_jsonl_gz(data / "dev.jsonl.gz"); labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    rows = [{"id": record["id"], "fragments": fragments(record)} for record in records]; by_id = {row["id"]: row for row in rows}
    items = {}
    for item in common.ITEMS:
        positives = [record["id"] for record in records if int(labels[record["id"]][item])]
        evidence_key = f"e{item[1:]}"; nonempty = [record_id for record_id in positives if labels[record_id][evidence_key]]
        metrics = {}
        for kind in ("line", "sentence"):
            covered = [record_id for record_id in nonempty if any(fragment["kind"] == kind and fragment["selectable"] and labels[record_id][evidence_key] in fragment["text"] for fragment in by_id[record_id]["fragments"])]
            metrics[f"{kind}_coverage_nonempty_gold_evidence"] = len(covered) / len(nonempty) if nonempty else None
            metrics[f"{kind}_uncovered_ids"] = sorted(set(nonempty) - set(covered))
        items[item] = {"positive_count": len(positives), "nonempty_gold_evidence_count": len(nonempty), "empty_gold_evidence_count": len(positives) - len(nonempty), **metrics}
    report = {"experiment_id": "inc048_source_fragment_ontology_audit", "method": "unchanged line and punctuation-bound sentence fragments; no predictions", "items": items, "fragment_counts": {"total": len([f for row in rows for f in row["fragments"]]), "lines": sum(f["kind"] == "line" for row in rows for f in row["fragments"]), "sentences": sum(f["kind"] == "sentence" for row in rows for f in row["fragments"]), "unselectable_over_500": sum(not f["selectable"] for row in rows for f in row["fragments"]), "document_types": dict(Counter(f["doc_type"] for row in rows for f in row["fragments"]))}}
    common.write_jsonl(output / "manifest.jsonl", rows); common.write_json(output / "report.json", report); print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
