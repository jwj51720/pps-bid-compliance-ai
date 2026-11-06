"""Offline provenance replay for frozen L41 v4 observations."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..config import load_experiment_config
from ..domain import NoticeRecord
from ..ingest import load_notice_records
from ..reference import FrozenL41Reference
from ..runtime.openrouter import atomic_json


def _read_csv(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _directory_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    for child in sorted(path.glob("*.json")):
        digest.update(child.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(child.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _confusion(
    labels: Mapping[str, Mapping[str, str]], predictions: Mapping[str, int],
) -> dict[str, int | float]:
    tp = sum(predictions[notice_id] == 1 and row["v4"] == "1" for notice_id, row in labels.items())
    fp = sum(predictions[notice_id] == 1 and row["v4"] == "0" for notice_id, row in labels.items())
    fn = sum(predictions[notice_id] == 0 and row["v4"] == "1" for notice_id, row in labels.items())
    denominator = 2 * tp + fp + fn
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "f1": (2 * tp / denominator) if denominator else 0.0,
    }


def _parse_v4_response(path: Path) -> dict[str, Any]:
    envelope = json.loads(path.read_text(encoding="utf-8"))
    content = json.loads(str(envelope["content"]))
    value = content.get("v4")
    if not isinstance(value, dict):
        raise ValueError(f"{path}: missing v4 object")
    if value.get("q") not in {"Y", "N", "U"}:
        raise ValueError(f"{path}: invalid q")
    if value.get("r") not in {"Y", "N", "U"}:
        raise ValueError(f"{path}: invalid r")
    if value.get("e") not in {"Y", "N", "U"}:
        raise ValueError(f"{path}: invalid e")
    if value.get("id") is not None and not isinstance(value.get("id"), str):
        raise ValueError(f"{path}: invalid id")
    return value


def _selected_source(
    record: NoticeRecord, candidates: Sequence[Mapping[str, Any]], source_id: str | None,
) -> dict[str, Any] | None:
    if source_id is None:
        return None
    matches = [row for row in candidates if row.get("id") == source_id]
    if len(matches) != 1:
        raise ValueError(f"{record.notice_id}: source ID {source_id!r} has {len(matches)} matches")
    selected = dict(matches[0])
    documents = {document.doc_id: document for document in record.documents}
    doc_id = str(selected.get("doc_id"))
    if doc_id not in documents:
        raise ValueError(f"{record.notice_id}: source points outside supplied documents")
    text = str(selected.get("text") or "")
    if not text or text not in documents[doc_id].text:
        raise ValueError(f"{record.notice_id}: source section is not an exact document substring")
    selected["document_sha256"] = documents[doc_id].sha256
    return selected


def _amount(record: NoticeRecord) -> int | None:
    value = (record.raw.get("meta") or {}).get("입찰추정가격")
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def run_v4_provenance_audit(
    *, repository_root: Path, reference_manifest_path: Path, labels_path: Path,
    baseline_path: Path, response_dir: Path, output_dir: Path,
) -> dict[str, Any]:
    """Replay stored v4 observations without changing any final label."""

    config = load_experiment_config(reference_manifest_path, repository_root)
    records = load_notice_records(config.input_path)
    record_by_id = {record.notice_id: record for record in records}
    labels = _read_csv(labels_path)
    baseline = _read_csv(baseline_path)
    expected_ids = set(record_by_id)
    response_paths = {path.stem: path for path in response_dir.glob("*.json")}
    coverages = {
        "input": set(record_by_id),
        "labels": set(labels),
        "baseline": set(baseline),
        "responses": set(response_paths),
    }
    if any(ids != expected_ids for ids in coverages.values()):
        detail = {key: len(value) for key, value in coverages.items()}
        raise ValueError(f"v4 audit ID coverage differs: {detail}")

    reference = FrozenL41Reference(config.reference_zip, config.reference_zip_sha256)
    builder = reference.builder(config.data_dir)
    observations: list[dict[str, Any]] = []
    selected_sources: dict[str, dict[str, Any] | None] = {}
    prepared_pools: dict[str, list[Mapping[str, Any]]] = {}
    for record in records:
        notice_id = record.notice_id
        observation = _parse_v4_response(response_paths[notice_id])
        prepared = reference.pipeline.prepare_record(dict(record.raw), builder)
        candidates = prepared["pool"]["candidates"]
        selected = _selected_source(record, candidates, observation.get("id"))
        prepared_pools[notice_id] = candidates
        selected_sources[notice_id] = selected
        observations.append({
            "id": notice_id,
            "q": observation["q"],
            "r": observation["r"],
            "e": observation["e"],
            "source_id": observation.get("id"),
            "source": selected,
            "estimated_price": _amount(record),
        })

    observation_by_id = {row["id"]: row for row in observations}
    baseline_values = {notice_id: int(row["v4"]) for notice_id, row in baseline.items()}
    q_and_r = {
        notice_id: int(row["q"] == "Y" and row["r"] == "Y")
        for notice_id, row in observation_by_id.items()
    }
    q_and_r_without_e = {
        notice_id: int(row["q"] == "Y" and row["r"] == "Y" and row["e"] == "N")
        for notice_id, row in observation_by_id.items()
    }
    baseline_confusion = _confusion(labels, baseline_values)
    q_and_r_confusion = _confusion(labels, q_and_r)
    without_e_confusion = _confusion(labels, q_and_r_without_e)
    baseline_f1 = float(baseline_confusion["f1"])
    without_e_f1 = float(without_e_confusion["f1"])

    positive_ids = {notice_id for notice_id, row in labels.items() if row["v4"] == "1"}
    error_ids = {
        notice_id for notice_id in expected_ids
        if baseline[notice_id]["v4"] != labels[notice_id]["v4"]
    }
    review_ids = positive_ids | error_ids
    for notice_id in sorted(review_ids):
        record = record_by_id[notice_id]
        atomic_json(output_dir / "review_packets" / f"{notice_id}.json", {
            "id": notice_id,
            "baseline_v4": int(baseline[notice_id]["v4"]),
            "gold_v4": int(labels[notice_id]["v4"]),
            "gold_e4": labels[notice_id]["e4"],
            "observation": observation_by_id[notice_id],
            "documents": [
                {
                    "doc_id": document.doc_id,
                    "type": document.document_type,
                    "order": document.order,
                    "sha256": document.sha256,
                    "text": document.text,
                }
                for document in record.documents
            ],
            "prepared_source_pool": prepared_pools[notice_id],
        })

    positive_below_230m = sorted(
        notice_id for notice_id in positive_ids
        if observation_by_id[notice_id]["estimated_price"] is not None
        and observation_by_id[notice_id]["estimated_price"] < 230_000_000
    )
    report = {
        "status": "PASS",
        "phase": "offline_provenance_replay_only",
        "records": len(records),
        "coverage": {key: len(ids) for key, ids in coverages.items()},
        "v4_parse_valid": len(observations),
        "non_null_source_ids": sum(row["source_id"] is not None for row in observations),
        "non_null_sources_resolved": sum(row["source"] is not None for row in observations),
        "counterfactuals": {
            "baseline_c005d": baseline_confusion,
            "stored_q_and_r": q_and_r_confusion,
            "stored_q_and_r_and_not_e": without_e_confusion,
            "not_e_macro_delta": (without_e_f1 - baseline_f1) / 24,
        },
        "price_gate_diagnostic": {
            "positive_count": len(positive_ids),
            "positive_below_230m_count": len(positive_below_230m),
            "positive_below_230m_ids": positive_below_230m,
            "hard_gate_recall_ceiling": (
                (len(positive_ids) - len(positive_below_230m)) / len(positive_ids)
                if positive_ids else 0.0
            ),
            "policy": "diagnostic only; no threshold label rule",
        },
        "baseline_error_ids": sorted(error_ids),
        "review_packet_ids": sorted(review_ids),
        "hashes": {
            "input": _sha256(config.input_path),
            "labels": _sha256(labels_path),
            "baseline": _sha256(baseline_path),
            "r10_response_directory": _directory_sha256(response_dir),
            "reference_zip": _sha256(config.reference_zip),
        },
        "label_use": "post-source-view metrics and review selection only",
        "llm_calls": 0,
        "final_label_changes": 0,
    }
    atomic_json(output_dir / "observation_ledger.json", observations)
    atomic_json(output_dir / "audit_report.json", report)
    return report
