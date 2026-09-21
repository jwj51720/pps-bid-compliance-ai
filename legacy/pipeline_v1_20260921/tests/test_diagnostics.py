from src.diagnostics import diagnose_experiment
from src.schema import ITEMS


def test_diagnostics_reconciles_macro_f1_and_output_budget() -> None:
    record = {
        "id": "r1",
        "docs": [{"doc_id": "d1", "type": "공고문", "text": "정답 근거"}],
        "meta": {},
    }
    label = {"id": "r1"}
    row = {"id": "r1"}
    judgment = {}
    for index, item in enumerate(ITEMS, 1):
        label[item] = "1" if item == "v1" else "0"
        label[f"e{index}"] = "정답 근거" if item == "v1" else ""
        row[item] = 1 if item == "v1" else 0
        row[f"e{index}"] = "정답 근거" if item == "v1" else ""
        judgment[item] = {
            "위반여부": row[item],
            "근거문구": row[f"e{index}"] or None,
        }
    import json

    prediction = {
        "id": "r1",
        "row": row,
        "raw_response": json.dumps(judgment, ensure_ascii=False),
        "usage": {"completion_tokens": 100},
    }

    result = diagnose_experiment(
        [record],
        [label],
        [prediction],
        max_document_chars=4000,
        max_completion_tokens=2500,
    )

    assert result["macro_f1"] == 1 / 24
    assert result["input"]["gold_evidence_in_context_rate"] == 1.0
    assert result["output"]["max_completion_limit_share"] == 0.04
