"""Competition output constants and the LLM response schema."""

from __future__ import annotations

from typing import Any

ITEMS = tuple(f"v{i}" for i in range(1, 25))
EVIDENCE_COLUMNS = tuple(f"e{i}" for i in range(1, 25))
SUBMISSION_COLUMNS = ("id", *ITEMS, *EVIDENCE_COLUMNS)
ABSENCE_ITEMS = frozenset({"v10", "v11", "v16", "v18", "v20"})
EVIDENCE_MAX_CHARS = 500
V8_COMPOSITE_STATES = ("없음", "실적", "지역", "둘다", "검토")


def judgment_schema(
    v8_composite_enabled: bool = False,
    items: tuple[str, ...] = ITEMS,
) -> dict[str, Any]:
    """Return the strict JSON schema for one all-item or item-group pass."""
    if not items or any(item not in ITEMS for item in items):
        raise ValueError("items must be a non-empty subset of v1..v24")
    if len(items) != len(set(items)):
        raise ValueError("items must not contain duplicates")
    properties: dict[str, Any] = {}
    for item in items:
        evidence_type: dict[str, Any]
        if item in ABSENCE_ITEMS:
            evidence_type = {"type": "null"}
        else:
            evidence_type = {"type": ["string", "null"], "maxLength": 2000}
        properties[item] = {
            "type": "object",
            "additionalProperties": False,
            "required": ["위반여부", "근거문구"],
            "properties": {
                "위반여부": {"type": "integer", "enum": [0, 1]},
                "근거문구": evidence_type,
            },
        }
    if v8_composite_enabled and "v8" in items:
        properties["v8병합관찰"] = {
            "type": "object",
            "additionalProperties": False,
            "required": ["상태", "관찰근거문구"],
            "properties": {
                "상태": {"type": "string", "enum": list(V8_COMPOSITE_STATES)},
                "관찰근거문구": {"type": ["string", "null"], "maxLength": 2000},
            },
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [*items, *( ["v8병합관찰"] if v8_composite_enabled and "v8" in items else [])],
        "properties": properties,
    }
