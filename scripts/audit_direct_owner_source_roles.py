"""Export fixed S019 source samples for human role review."""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pps_ai.reference.frozen import FrozenL41Reference
from src.pps_ai.runtime.openrouter import atomic_json


ITEMS = ("v1", "v2", "v5", "v6", "v7", "v8")
META_KEYS = ("적용계약법", "업무구분", "계약방법", "낙찰방법", "입찰추정가격", "소관구분")


def main() -> None:
    s019 = json.loads((ROOT / "outputs/clean-exp-s019-python-policy-population-audit-v1/audit_report.json").read_text())
    manifest = json.loads((ROOT / "experiments/manifests/clean_exp_s001_integrated_v3_v19_v1.json").read_text())
    reference = FrozenL41Reference(ROOT / manifest["reference"]["zip_path"], manifest["reference"]["zip_sha256"])
    modules = {
        "v1": importlib.import_module("dev.run_v1_organization_capacity_experiment_v3"),
        "v2": importlib.import_module("dev.run_v2_notice_effect_experiment"),
        "v5": importlib.import_module("dev.run_v5_amount_region_experiment_v2"),
        "v6": importlib.import_module("dev.run_v6_basic_region_experiment"),
        "v7": importlib.import_module("dev.run_v7_multi_province_experiment"),
        "v8": importlib.import_module("dev.run_v8_fact_intersection_experiment"),
    }
    selected = {
        item: s019["comparisons"][item + "_final"]["population_hash_sample_ids"][:8]
        for item in ITEMS
    }
    selected["v6_exception"] = s019["comparisons"]["v6_exception_on_hit"]["population_hash_sample_ids"][:8]
    wanted = {record_id for ids in selected.values() for record_id in ids}
    records = {
        str(record["id"]): record
        for record in reference.baseline.iter_records(str(ROOT / "data/raw/open/train_unlabeled.jsonl.gz"))
        if str(record["id"]) in wanted
    }
    if set(records) != wanted:
        raise ValueError("fixed S019 sample ID missing")
    cases = []
    for owner, ids in selected.items():
        for record_id in ids:
            record = records[record_id]
            if owner == "v1":
                hits = [hit[1] for hit in modules["v1"].same_line_candidate_hits(record, "plus_all_manufacturer_registration")]
            elif owner == "v2":
                hits = modules["v2"].notice_hits(record)
            elif owner == "v5":
                hits = modules["v5"].strict_region_hits(record)
            elif owner in ("v6", "v6_exception"):
                hits = modules["v6"].region_hits(record)
            elif owner == "v7":
                hits = modules["v7"].multi_province_hits(record)
            else:
                _, _, detail = modules["v8"].predict(record, use_quote_exception=True)
                hits = [detail["first_performance"], detail["first_region"]]
            source = []
            for hit in hits[:2]:
                for doc in record.get("docs") or []:
                    offset = str(doc.get("text") or "").find(hit)
                    if offset >= 0:
                        text = str(doc["text"])
                        source.append({
                            "doc_id": doc.get("doc_id"), "type": doc.get("type"),
                            "hit": hit[:700],
                            "context": text[max(0, offset - 200):min(len(text), offset + len(hit) + 200)][:1200],
                        })
                        break
            cases.append({
                "owner": owner, "id": record_id,
                "meta": {key: (record.get("meta") or {}).get(key) for key in META_KEYS},
                "source": source,
                "hit_count": len(hits),
                "has_attachment": any(doc.get("type") != "공고문" for doc in record.get("docs") or []),
            })
    output = ROOT / "outputs/clean-exp-s020-direct-owner-source-role-audit-v1"
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "PASS" if len(cases) == 56 else "FAIL",
        "base_manifest": "experiments/manifests/clean_exp_s001_integrated_v3_v19_v1.json",
        "allowed_policy_changes": [],
        "reference_zip_sha256": manifest["reference"]["zip_sha256"],
        "s019_sha256": hashlib.sha256((ROOT / "outputs/clean-exp-s019-python-policy-population-audit-v1/audit_report.json").read_bytes()).hexdigest(),
        "llm_calls": 0, "embedding_calls": 0,
        "cases": cases,
    }
    atomic_json(output / "source_samples.json", report)
    print(report["status"], len(cases), len(records))


if __name__ == "__main__":
    main()
