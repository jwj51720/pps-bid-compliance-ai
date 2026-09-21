"""C002RA reducer with field-level 4-digit industry-code provenance."""

from __future__ import annotations

import re
from typing import Any, Mapping

from .v24_multi_observation import (
    _amount_in_source,
    _canonical_region,
    _contract_method,
    _digits,
    _evidence,
    _industry_codes,
    _parse_response,
    _region_set,
    _source_contains,
)
from ..views.v24_multi_observation import candidate_index


def _valid_four_digit_codes(source_text: str, values: list[str]) -> list[str]:
    return sorted({
        value
        for value in values
        if re.fullmatch(r"[0-9]{4}", value) and value in source_text
    })


def decide_v24_code_provenance_v21(
    record: Mapping[str, Any],
    view: Mapping[str, Any],
    response: Mapping[str, Any],
) -> tuple[int, str, dict[str, Any]]:
    parsed = _parse_response(response)
    if parsed is None:
        return 0, "", {"valid": False, "fallback": True, "observations": {}, "mismatches": []}
    sources = candidate_index(view)
    accepted: dict[str, list[dict[str, Any]]] = {axis: [] for axis in parsed}
    for axis, rows in parsed.items():
        for row in rows:
            source = sources.get(row["source_id"])
            axis_source_valid = source is not None and source.axis == axis
            diagnostic = {**row, "source_valid": axis_source_valid, "source": source}
            if axis_source_valid and axis == "amount" and row["value_won"] is not None:
                diagnostic["source_valid"] = _amount_in_source(source.text, row["value_won"])
            elif axis_source_valid and axis == "region":
                diagnostic["source_valid"] = all(
                    _source_contains(source.text, value) for value in row["regions"]
                )
            elif axis_source_valid and axis == "industry":
                valid_codes = _valid_four_digit_codes(source.text, row["industry_codes"])
                valid_names = sorted({
                    value for value in row["industry_names"]
                    if _source_contains(source.text, value)
                })
                diagnostic["valid_industry_codes"] = valid_codes
                diagnostic["valid_industry_names"] = valid_names
                diagnostic["rejected_industry_codes"] = sorted(
                    set(row["industry_codes"]) - set(valid_codes)
                )
            accepted[axis].append(diagnostic)

    meta = record.get("meta") or {}
    mismatches: list[dict[str, Any]] = []
    amount_meta = {
        "BUDGET_TOTAL": _digits(meta.get("배정예산금액")),
        "ESTIMATED_EX_VAT": _digits(meta.get("입찰추정가격")),
    }
    for row in accepted["amount"]:
        expected = amount_meta.get(row["role"])
        actual = _digits(row["value_won"])
        if row["source_valid"] and expected is not None and actual is not None and actual != expected:
            mismatches.append({"axis": "amount", "source": row["source"], "expected": expected, "actual": actual})

    expected_contract = _contract_method(meta.get("계약방법"))
    for row in accepted["contract"]:
        if (
            row["source_valid"]
            and row["role"] == "COMPETITION_METHOD"
            and expected_contract is not None
            and row["competition_method"] not in {"UNKNOWN", "OTHER", expected_contract}
        ):
            mismatches.append({
                "axis": "contract", "source": row["source"],
                "expected": expected_contract, "actual": row["competition_method"],
            })

    expected_regions = _region_set(meta.get("제한지역코드목록"))
    region_limited = str(meta.get("지역제한여부") or "").upper() == "Y"
    region_rows = [
        row for row in accepted["region"]
        if row["source_valid"] and row["role"] == "BIDDER_LOCATION" and row["regions"]
    ]
    actual_regions = {
        _canonical_region(value) for row in region_rows for value in row["regions"]
    }
    if actual_regions and ((not region_limited) or (expected_regions and actual_regions != expected_regions)):
        mismatches.append({
            "axis": "region", "source": region_rows[0]["source"],
            "expected": sorted(expected_regions), "actual": sorted(actual_regions),
        })

    expected_codes = _industry_codes(meta.get("면허업종제한목록"))
    industry_limited = str(meta.get("업종제한여부") or "").upper() == "Y"
    industry_rows = [
        row for row in accepted["industry"]
        if row["source_valid"] and row["role"] == "BIDDER_MANDATORY_INDUSTRY"
        and row.get("valid_industry_codes")
    ]
    actual_codes = {
        code for row in industry_rows for code in row["valid_industry_codes"]
    }
    if actual_codes and ((not industry_limited) or (expected_codes and actual_codes != expected_codes)):
        mismatches.append({
            "axis": "industry", "source": industry_rows[0]["source"],
            "expected": sorted(expected_codes), "actual": sorted(actual_codes),
        })

    diagnostic_observations = {
        axis: [{key: value for key, value in row.items() if key != "source"} for row in rows]
        for axis, rows in accepted.items()
    }
    diagnostic_mismatches = [
        {key: value for key, value in item.items() if key != "source"}
        for item in mismatches
    ]
    if not mismatches:
        return 0, "", {
            "valid": True,
            "fallback": False,
            "observations": diagnostic_observations,
            "mismatches": [],
        }
    source = mismatches[0]["source"]
    evidence = _evidence(source)
    original = str(record["docs"][source.document_order]["text"])
    if not evidence or evidence not in original:
        return 0, "", {
            "valid": False,
            "fallback": True,
            "observations": diagnostic_observations,
            "mismatches": diagnostic_mismatches,
            "reason": "positive evidence is not an exact source substring",
        }
    return 1, evidence, {
        "valid": True,
        "fallback": False,
        "observations": diagnostic_observations,
        "mismatches": diagnostic_mismatches,
    }
