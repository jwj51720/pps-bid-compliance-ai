from scripts.select_equivalence_sample import select_ids
from src.schema import ITEMS


def test_select_ids_covers_each_item_and_fills_with_low_positive_rows() -> None:
    rows = []
    for index, item in enumerate(ITEMS):
        row = {"id": f"positive-{index}", **{candidate: "0" for candidate in ITEMS}}
        row[item] = "1"
        rows.append(row)
    rows.extend(
        [
            {"id": "all-negative", **{item: "0" for item in ITEMS}},
            {"id": "extra-positive", **{item: "1" for item in ITEMS}},
        ]
    )

    selected = select_ids(rows, target_positive_per_item=1, sample_size=25)

    assert len(selected) == 25
    assert "extra-positive" in selected
    assert "all-negative" in selected
