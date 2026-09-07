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
    output_mode: str = "labels_and_evidence",
) -> dict[str, Any]:
    """Return the strict JSON schema for one all-item or item-group pass."""
    if not items or any(item not in ITEMS for item in items):
        raise ValueError("items must be a non-empty subset of v1..v24")
    if len(items) != len(set(items)):
        raise ValueError("items must not contain duplicates")
    if output_mode not in {"labels_and_evidence", "labels_only", "labels_and_anchor", "labels_and_sparse_evidence"}:
        raise ValueError("output_mode must be labels_and_evidence, labels_only, or labels_and_anchor")
    if output_mode == "labels_only" and v8_composite_enabled:
        raise ValueError("labels_only does not support v8 composite observations")
    properties: dict[str, Any] = {}
    if output_mode == "labels_and_sparse_evidence":
        # This is a serialization-only variant of labels_and_evidence.  The
        # decision semantics stay identical: labels are still final decisions,
        # every non-absence positive still needs an exact source excerpt, and
        # absence review is audit information only (never a Python override).
        absence_items = [item for item in items if item in ABSENCE_ITEMS]
        properties["판정"] = {
            "type": "object",
            "additionalProperties": False,
            "required": list(items),
            "properties": {item: {"type": "integer", "enum": [0, 1]} for item in items},
        }
        properties["발췌"] = {
            "type": "array",
            "maxItems": len([item for item in items if item not in ABSENCE_ITEMS]),
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["항목", "근거문구"],
                "properties": {
                    "항목": {"type": "string", "enum": [item for item in items if item not in ABSENCE_ITEMS]},
                    "근거문구": {"type": "string", "minLength": 1, "maxLength": 2000},
                },
            },
        }
        properties["부재검토"] = {
            "type": "object",
            "additionalProperties": False,
            "required": absence_items,
            "properties": {
                item: {"type": "string", "enum": ["필수조건_확인", "미확인", "비적용_또는_불명"]}
                for item in absence_items
            },
        }
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["판정", "발췌", "부재검토"],
            "properties": properties,
        }
    for item in items:
        if output_mode == "labels_only":
            properties[item] = {"type": "integer", "enum": [0, 1]}
            continue
        if output_mode == "labels_and_anchor":
            anchor_type: dict[str, Any] = {"type": "null"} if item in ABSENCE_ITEMS else {"type": ["string", "null"], "minLength": 12, "maxLength": 120}
            properties[item] = {
                "type": "object", "additionalProperties": False,
                "required": ["위반여부", "판단어구"],
                "properties": {"위반여부": {"type": "integer", "enum": [0, 1]}, "판단어구": anchor_type},
            }
            continue
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
