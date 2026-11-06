"""Source-complete deterministic overrides frozen before EXP-123 packaging."""

from __future__ import annotations

import re
from typing import Any

NOTICE_AMOUNT_WON = 230_000_000
AMOUNT = re.compile(r"(?P<n>\d{1,3}(?:,\d{3})+)\s*원")
EOK = re.compile(r"(?P<n>\d+(?:\.\d+)?)\s*억\s*원?")
EOK_CHEON = re.compile(r"(?P<eok>\d+(?:\.\d+)?)\s*억\s*(?P<cheon>\d+(?:\.\d+)?)\s*천\s*만?\s*원?")
CHEON_MAN = re.compile(r"(?P<n>\d+(?:\.\d+)?)\s*천\s*만\s*원")
MAN = re.compile(r"(?P<n>\d+(?:\.\d+)?)\s*만\s*원")
LOWER = re.compile(r"(?:이상|초과)")
V2_ROLE = re.compile(r"(?:실적이\s*있는\s*(?:자|업체)|이상인\s*업체|보유한\s*업체|실적이\s*있어야)")
V21 = re.compile(r"(?:최소\s*)?(?:계약참여\s*)?(?:지분율|참여지분율|출자비율)[^\n]{0,50}?(\d+(?:\.\d+)?)\s*%")


def _amounts(text: str) -> list[int]:
    values = [int(match.group("n").replace(",", "")) for match in AMOUNT.finditer(text)]
    values += [round(float(match.group("eok")) * 100_000_000 + float(match.group("cheon")) * 10_000_000) for match in EOK_CHEON.finditer(text)]
    values += [round(float(match.group("n")) * 100_000_000) for match in EOK.finditer(text)]
    values += [round(float(match.group("n")) * 10_000_000) for match in CHEON_MAN.finditer(text)]
    values += [round(float(match.group("n")) * 10_000) for match in MAN.finditer(text)]
    return sorted(set(values))


def _lines(record: dict[str, Any]):
    for document in record["docs"]:
        for raw in document["text"].splitlines(keepends=True):
            yield raw.rstrip("\r\n")


def _evidence_window(line: str, focus: int) -> str:
    """Keep a bounded unchanged source substring containing the rule trigger."""
    if len(line) <= 500:
        return line
    start = max(0, min(focus - 220, len(line) - 500))
    return line[start : start + 500]


def _v2(record: dict[str, Any]) -> str:
    estimate = record["meta"].get("입찰추정가격")
    try:
        below = int(estimate) < NOTICE_AMOUNT_WON
    except (TypeError, ValueError):
        below = False
    if not below or "공사" in str(record["meta"].get("업무구분") or ""):
        return ""
    for line in _lines(record):
        if "실적" in line and LOWER.search(line) and _amounts(line) and V2_ROLE.search(line):
            return _evidence_window(line, line.find("실적"))
    return ""


def _v3(record: dict[str, Any]) -> str:
    try:
        budget = int(record["meta"].get("배정예산금액"))
    except (TypeError, ValueError):
        return ""
    terms = ("보유", "제출", "있는 업체", "있어야", "입찰참가자격")
    for line in _lines(record):
        values = _amounts(line)
        if "실적" in line and LOWER.search(line) and len(values) == 1 and any(term in line for term in terms) and values[0] >= budget:
            return _evidence_window(line, line.find("실적"))
    return ""


def _v21(record: dict[str, Any]) -> str:
    form = str(record["meta"].get("공동도급구성방식") or "")
    if "분담이행" in form:
        return ""
    threshold = 10.0 if record["meta"].get("적용계약법") == "국가계약법" else 5.0 if record["meta"].get("적용계약법") == "지방계약법" else None
    if threshold is None:
        return ""
    for line in _lines(record):
        match = V21.search(line)
        if match and "분담이행" not in line and float(match.group(1)) < threshold:
            return _evidence_window(line, match.start())
    return ""


def apply_frozen_rules(record: dict[str, Any], judgment: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {item: dict(value) for item, value in judgment.items()}
    for item, evidence in (("v2", _v2(record)), ("v3", _v3(record)), ("v21", _v21(record))):
        result[item] = {"위반여부": int(bool(evidence)), "근거문구": evidence}
    return result
