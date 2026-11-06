"""Summarize the isolated v18 card/output ablation, without label corrections."""

import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import load_config


def main() -> None:
    names = [
        ("314-v18-only-existing-card-ve", "fast-panel-c4"),
        ("315-v18-absence-card-ve", "fast-panel-c4"),
        ("316-v18-absence-card-vonly", "fast-panel-c4"),
        ("317-v18-only-existing-card-ve", "holdout-c4"),
        ("318-v18-absence-card-ve", "holdout-c4"),
    ]
    report = {}
    for name, suffix in names:
        directory = Path("outputs") / f"exp-{name}-{suffix}"
        if not (directory / "run_meta.json").exists():
            report[name] = {"status": "not_terminal"}
            continue
        meta = json.loads((directory / "run_meta.json").read_text())
        predictions = [json.loads(line) for line in
                       (directory / "predictions.jsonl").read_text().splitlines()]
        with (directory / "per_item_metrics.csv").open() as stream:
            metrics = next(row for row in csv.DictReader(stream) if row["item"] == "v18")
        validation = json.loads((directory / "validation.json").read_text())
        config = load_config(f"configs/config.exp{name}-{suffix}.yaml")
        report[name] = {
            "status": "complete", "target_metrics": metrics,
            "configured_max_tokens": config.llm.max_tokens,
            "generation_anomalies": [
                {"id": row["id"], "finish_reason": row["finish_reason"],
                 "reported_completion_tokens": row["usage"].get("completion_tokens"),
                 "raw_characters": len(row["raw_response"])}
                for row in predictions
                if row["usage"].get("completion_tokens", 0) > config.llm.max_tokens
                or row["finish_reason"] == "length"
            ],
            "records": len(predictions),
            "successful_model_passes": sum(len(row["pass_judgments"]) for row in predictions),
            "parse_errors": sum(len(row["parse_errors"]) for row in predictions),
            "e18_all_blank": all(not row["row"]["e18"] for row in predictions),
            "v18_postprocess_changes": [row["id"] for row in predictions
                if row["judgment"]["v18"] !=
                row["decision_provenance"]["model_judgment"]["v18"]],
            "positive_ids": [row["id"] for row in predictions if row["row"]["v18"]],
            "runtime_seconds": meta["runtime_seconds"], "usage": meta["usage"],
            "validation": validation,
            "note": "Inactive-item/frozen-rule macro score is not this subset's quality metric.",
        }
    destination = Path("outputs/exp314-exp316-v18-comparison")
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
