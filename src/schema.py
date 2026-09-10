"""Competition output constants and the LLM response schema."""

from __future__ import annotations

from typing import Any

ITEMS = tuple(f"v{i}" for i in range(1, 25))
EVIDENCE_COLUMNS = tuple(f"e{i}" for i in range(1, 25))
SUBMISSION_COLUMNS = ("id", *ITEMS, *EVIDENCE_COLUMNS)
ABSENCE_ITEMS = frozenset({"v10", "v11", "v16", "v18", "v20"})
EVIDENCE_MAX_CHARS = 500
V8_COMPOSITE_STATES = ("없음", "실적", "지역", "둘다", "검토")
TRIAGE_STATES = ("명시근거", "부재검토", "불명확", "해당없음")
FACT_INVENTORY_CATEGORIES = (
    "참가자격_실적_지역",
    "제품_기업_직접생산",
    "규격_모델_기술요구",
    "제출서류_확약서",
    "계약방식_공동계약",
    "일정_설명회",
    "금액_메타대조",
)
FACT_INVENTORY_CATEGORIES_V2 = (
    *FACT_INVENTORY_CATEGORIES,
    "예외_허용_적용범위",
)
TIMELINE_FACT_ROLES = (
    "공고일", "현장설명회일시", "제안서_접수마감", "가격입찰_마감", "긴급_재공고_표시",
)
PROCEDURE_FACT_FIELDS = (
    "참가자격_관계",
    "제품자격_관계",
    "규격요구_관계",
    "제출서류_관계",
    "공동계약_관계",
    "일정참가_관계",
    "공고메타_대조값",
)


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


def triage_schema(items: tuple[str, ...] = ITEMS) -> dict[str, Any]:
    """Strict route-state payload for the non-final first B-stage call."""
    if not items or any(item not in ITEMS for item in items) or len(items) != len(set(items)):
        raise ValueError("triage items must be a non-empty unique subset of v1..v24")
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(items),
        "properties": {
            item: {"type": "string", "enum": list(TRIAGE_STATES)} for item in items
        },
    }


def locator_schema(items: tuple[str, ...] = ITEMS) -> dict[str, Any]:
    """Schema for non-final source-navigation excerpts.

    A null means only that the locator found no safe substring in the supplied
    material.  It has no label semantics and is never a final negative.
    """
    if not items or any(item not in ITEMS or item in ABSENCE_ITEMS for item in items):
        raise ValueError("locator items must be a non-empty non-absence subset of v1..v24")
    if len(items) != len(set(items)):
        raise ValueError("locator items must not contain duplicates")
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(items),
        "properties": {
            item: {"type": ["string", "null"], "maxLength": 2000}
            for item in items
        },
    }


def inventory_schema(items: tuple[str, ...] = ITEMS) -> dict[str, Any]:
    """Non-final source-inventory schema for every active item.

    ``null`` is only a pack-local observation: it never means a final negative.
    Unlike locator_schema, absence items are deliberately included so the
    pipeline can retain pack-level presence observations for AND review.
    """
    if not items or any(item not in ITEMS for item in items):
        raise ValueError("inventory items must be a non-empty subset of v1..v24")
    if len(items) != len(set(items)):
        raise ValueError("inventory items must not contain duplicates")
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(items),
        "properties": {
            item: {"type": ["string", "null"], "maxLength": 500}
            for item in items
        },
    }


def fact_inventory_schema(
    max_items: int = 3,
    categories: tuple[str, ...] = FACT_INVENTORY_CATEGORIES,
) -> dict[str, Any]:
    """Schema for source-only factual excerpts, never labels or v keys."""
    if max_items not in {3, 4}:
        raise ValueError("fact inventory max_items must be 3 or 4")
    if categories not in {FACT_INVENTORY_CATEGORIES, FACT_INVENTORY_CATEGORIES_V2}:
        raise ValueError("fact inventory categories must be a supported version")
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(categories),
        "properties": {
            category: {
                "type": "array",
                "maxItems": max_items,
                "items": {"type": "string", "minLength": 1, "maxLength": 360},
            }
            for category in categories
        },
    }


def timeline_fact_schema() -> dict[str, Any]:
    """Schema for source-only v23 timeline facts, never labels."""
    return {
        "type": "object", "additionalProperties": False,
        "required": list(TIMELINE_FACT_ROLES),
        "properties": {role: {"type": "array", "maxItems": 2,
            "items": {"type": "string", "minLength": 1, "maxLength": 360}}
            for role in TIMELINE_FACT_ROLES},
    }


def procedure_fact_schema() -> dict[str, Any]:
    """Schema for EXP181 source-only relation navigation, never labels."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(PROCEDURE_FACT_FIELDS),
        "properties": {
            field: {
                "type": "array",
                "maxItems": 2,
                "items": {"type": "string", "minLength": 1, "maxLength": 360},
            }
            for field in PROCEDURE_FACT_FIELDS
        },
    }


def item_fact_schema() -> dict[str, Any]:
    """Schema for EXP188's one source-only candidate per item."""
    return {
        "type": "object", "additionalProperties": False, "required": list(ITEMS),
        "properties": {item: {"type": ["string", "null"], "maxLength": 180} for item in ITEMS},
    }
