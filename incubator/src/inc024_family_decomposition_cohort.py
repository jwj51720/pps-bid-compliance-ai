#!/usr/bin/env python3
"""Compile the pre-registered, label-stratified INC-024 mechanism cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FAMILIES = {
    "qualification_geo": ("v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9"),
    "products": ("v10", "v11", "v12", "v13", "v14", "v15", "v16", "v17", "v18"),
    "procedure": ("v19", "v21", "v22", "v23"),
    "sw_meta": ("v20", "v24"),
}


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = json.loads((root() / args.config).read_text(encoding="utf-8"))
    data_root = root() / config["data_root"]
    labels_path = data_root / "dev_labels.csv"
    with labels_path.open(encoding="utf-8") as handle:
        import csv
        labels = sorted(csv.DictReader(handle), key=lambda row: row["id"])

    selected: list[dict[str, str]] = []
    selected_ids: set[str] = set()
    per_family = config["positives_per_family"]
    for family, items in FAMILIES.items():
        choices = [row for row in labels if any(row[item] == "1" for item in items)]
        taken = 0
        for row in choices:
            if row["id"] in selected_ids:
                continue
            selected.append(row)
            selected_ids.add(row["id"])
            taken += 1
            if taken == per_family:
                break
        if taken != per_family:
            raise ValueError(f"family {family} has only {taken} non-overlapping positive selections")

    for row in labels:
        if len(selected) == config["cohort_size"]:
            break
        if row["id"] not in selected_ids and all(row[item] == "0" for items in FAMILIES.values() for item in items):
            selected.append(row)
            selected_ids.add(row["id"])
    if len(selected) != config["cohort_size"]:
        raise ValueError("not enough all-negative rows to fill cohort")

    ordered_ids = [row["id"] for row in selected]
    manifest = {
        "experiment_id": config["experiment_id"],
        "selection_rule": "per family, ascending ID positives without replacement; then ascending-ID all-negative fill",
        "families": FAMILIES,
        "positive_per_family": per_family,
        "cohort_size": config["cohort_size"],
        "ordered_ids": ordered_ids,
        "id_sha256": hashlib.sha256("\n".join(ordered_ids).encode("utf-8")).hexdigest(),
        "source_sha256": {"dev_labels": sha256_file(labels_path)},
        "family_gold_positive_counts": {
            family: sum(any(row[item] == "1" for item in items) for row in selected)
            for family, items in FAMILIES.items()
        },
        "all_negative_count": sum(all(row[item] == "0" for items in FAMILIES.values() for item in items) for row in selected),
    }
    output = root() / config["output_path"]
    write_json(output, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
