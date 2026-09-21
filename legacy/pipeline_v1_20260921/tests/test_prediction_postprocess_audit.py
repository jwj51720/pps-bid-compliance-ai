from scripts.audit_prediction_postprocess import model_judgment_from_saved
from src.schema import ITEMS


def _judgment(value: int = 0):
    return {item: {"위반여부": value, "근거문구": ""} for item in ITEMS}


def test_audit_prefers_explicit_decision_provenance() -> None:
    model = _judgment()
    model["v2"] = {"위반여부": 1, "근거문구": "근거"}
    row = {
        "id": "A",
        "decision_provenance": {"model_judgment": model},
        "pass_judgments": [_judgment()],
    }
    assert model_judgment_from_saved(row, "per_pass_and") == model


def test_audit_reconstructs_historical_absence_and_nonabsence_merge() -> None:
    first = _judgment()
    second = _judgment()
    first["v1"] = {"위반여부": 1, "근거문구": "첫 근거"}
    first["v10"] = {"위반여부": 1, "근거문구": ""}
    row = {"id": "A", "pass_judgments": [first, second]}

    model = model_judgment_from_saved(row, "per_pass_and")

    assert model["v1"] == {"위반여부": 1, "근거문구": "첫 근거"}
    assert model["v10"] == {"위반여부": 0, "근거문구": ""}
