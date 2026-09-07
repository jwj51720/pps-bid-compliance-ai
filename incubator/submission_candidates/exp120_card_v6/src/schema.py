"""Competition output constants and the LLM response schema."""

from __future__ import annotations

from typing import Any

ITEMS = tuple(f"v{i}" for i in range(1, 25))
EVIDENCE_COLUMNS = tuple(f"e{i}" for i in range(1, 25))
SUBMISSION_COLUMNS = ("id", *ITEMS, *EVIDENCE_COLUMNS)
ABSENCE_ITEMS = frozenset({"v10", "v11", "v16", "v18", "v20"})
EVIDENCE_MAX_CHARS = 500


def judgment_schema() -> dict[str, Any]:
    """Return the strict JSON schema used for one notice prediction."""
    properties: dict[str, Any] = {}
    for item in ITEMS:
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
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(ITEMS),
        "properties": properties,
    }
