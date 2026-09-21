"""Atomic organizer-format CSV export for active clean pipelines."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Mapping, Sequence


COLUMNS = ["id"] + [f"v{index}" for index in range(1, 25)] + [
    f"e{index}" for index in range(1, 25)
]


def write_submission_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            if list(row) != COLUMNS:
                raise ValueError("submission row column order differs")
            writer.writerow(row)
    temporary.replace(path)
