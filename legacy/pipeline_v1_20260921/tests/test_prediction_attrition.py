import json

from scripts.analyze_prediction_attrition import ITEMS, audit, raw_judgment


def make_record():
    judgment = {item: {"위반여부": 0, "근거문구": ""} for item in ITEMS}
    return {"id": "x", "judgment": judgment, "raw_response": json.dumps(judgment),
            "pass_judgments": [judgment], "parse_errors": [], "finish_reason": "stop",
            "decision_provenance": {"model_judgment": judgment}}


def test_raw_audit_excludes_multipass_and_staged():
    record = make_record()
    assert raw_judgment(record) is not None
    record["pass_judgments"] *= 2
    assert raw_judgment(record) is None
    record = make_record()
    record["staged_run"] = {"mode": "inventory"}
    assert raw_judgment(record) is None


def test_raw_audit_rejects_partial_or_malformed_and_accepts_known_wrapper():
    record = make_record()
    record["raw_response"] = '{"v1": 1}'
    assert raw_judgment(record) is None
    record["raw_response"] = '{"v1": '
    assert raw_judgment(record) is None
    record["raw_response"] = json.dumps({"判定": record["judgment"]})
    assert raw_judgment(record) is None
    record["raw_response"] = json.dumps({"판정": record["judgment"]})
    assert raw_judgment(record) is not None


def test_audit_counts_parse_errors_without_reclassifying_predictions(tmp_path):
    record = make_record()
    record["parse_errors"] = [{"error": "malformed"}]
    (tmp_path / "predictions.jsonl").write_text(json.dumps(record) + "\n")
    gold = {"x": {item: int(item == "v9") for item in ITEMS}}
    report = audit(tmp_path, gold)
    assert report["errors_on_parse_records"] == {"FN": 1}
    assert report["errors_on_clean_records"] == {}
    assert report["raw_to_model_label_changes"] == []
    assert record["judgment"]["v9"]["위반여부"] == 0


def test_audit_distinguishes_raw_normalization_from_postprocess(tmp_path):
    record = make_record()
    raw = json.loads(record["raw_response"])
    raw["v9"]["위반여부"] = 1
    record["raw_response"] = json.dumps(raw)
    (tmp_path / "predictions.jsonl").write_text(json.dumps(record) + "\n")
    gold = {"x": {item: 0 for item in ITEMS}}
    report = audit(tmp_path, gold)
    assert report["raw_to_model_label_changes"] == [
        {"id": "x", "item": "v9", "raw": 1, "model": 0, "gold": 0}]
    assert report["model_to_final_label_changes"] == []
