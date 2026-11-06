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
V6_GEOGRAPHY_FACT_FIELDS = (
    "참가자격_지역문구",
    "현장납품지_지역문구",
    "계약방식_절차문구",
    "지역범위_보충문구",
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
V24_COMPARISON_FIELDS = ("예산", "계약방법", "지역제한", "업종")
V24_COMPARISON_RELATIONS = ("양립가능", "양립불가능", "판단불가")
V4_PRESENCE_STATES = ("있음", "없음", "불명")
V4_CLAUSE_ROLES = (
    "참가자격",
    "제안평가_배점",
    "증빙서류_행정",
    "시설_조직_제품_기술조건",
    "기타",
    "불명",
)
V4_CLIENT_SCOPES = (
    "특정발주기관만",
    "민간_공공_또는_모든기관인정",
    "발주기관제한없음",
    "불명",
)
V4_PERFORMANCE_SCOPES = (
    "동등유사배제_좁은실적만",
    "폭넓은동등유사실적인정",
    "일반적인동종동일목적실적",
    "실적제한아님",
    "불명",
)
V5_THRESHOLD_BRANCHES = (
    "국가일반",
    "공기업준정부기관",
    "지방세종시군구",
    "지방기타시도",
    "별도기준용역",
    "불명",
)
V5_AMOUNT_RELATIONS = ("이상", "미만", "불명")
V5_REGION_ROLES = ("참가자격", "현장납품지", "지역명기타", "없음", "불명")
V6_REGION_ROLES = ("참가자격", "현장납품지", "지역명기타", "없음", "불명")
V6_BASIC_REGION_STATES = ("포함", "미포함", "불명")
V6_PROCEDURE_STATES = ("제한경쟁", "2인이상견적수의", "기타", "불명")
V6_EXCEPTION_STATES = ("충족", "불충족", "불명")
V10_APPLICABILITY_STATES = ("적용", "비적용", "불명")
V10_CONDITION_STATES = ("충족", "불충족", "조건없음", "불명")
V10_PRESENCE_STATES = ("있음", "없음", "불명")
V12_CANDIDATE_SOURCES = ("metadata", "공고자료", "둘다", "없음", "불명")
V12_TARGET_RELATIONS = ("동일대상", "다른대상", "불명")
V12_REQUIREMENT_ROLES = ("참가자격", "계약이행일반", "서류안내", "없음", "불명")
V12_EXCEPTION_STATES = ("있음", "없음", "불명")
V13_CLAUSE_ROLES = ("참가자격", "평가우대", "서류안내", "없음", "불명")
V13_MEDIUM_BUSINESS_STATES = ("가능", "불가", "불명")
V13_EXCEPTION_STATES = ("소액수의", "기타명시", "없음", "불명")
V23_LAW_STATES = ("지방계약", "국가계약", "불명")
V23_CONTRACT_STATES = ("협상", "기타", "불명")
V23_AMOUNT_BANDS = ("10억이상", "1억이상10억미만", "1억미만", "불명")
V23_DEADLINE_ROLES = ("현장설명회", "제안서마감", "없음", "불명")
V23_URGENT_STATES = ("긴급", "재공고", "해당없음", "불명")
V19_DOCUMENT_KINDS = (
    "물품공급·기술지원확약서", "일반확약서", "기타서류", "없음", "불명",
)
V19_REQUIRED_ACTIONS = (
    "발급·보유", "제출", "제출가능자격", "언급만", "없음", "불명",
)
V19_TIMING_STATES = (
    "입찰·제안전", "입찰마감후·낙찰전", "계약체결·납품", "복수시점", "없음", "불명",
)
V19_BID_EFFECTS = (
    "미제출·미보유시참가배제", "필수제출", "계약이행", "목록·서식", "없음", "불명",
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


def v24_fact_first_judgment_schema(
    items: tuple[str, ...] = ITEMS,
) -> dict[str, Any]:
    """Return a one-call observable v24 review followed by final V/E."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["v24대조", "판정"],
        "properties": {
            "v24대조": {
                "type": "array",
                "maxItems": len(V24_COMPARISON_FIELDS),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["필드", "원문값", "메타값", "관계"],
                    "properties": {
                        "필드": {"type": "string", "enum": list(V24_COMPARISON_FIELDS)},
                        "원문값": {"type": ["string", "null"], "maxLength": 500},
                        "메타값": {"type": ["string", "null"], "maxLength": 300},
                        "관계": {"type": "string", "enum": list(V24_COMPARISON_RELATIONS)},
                    },
                },
            },
            "판정": judgment_schema(items=items),
        },
    }


def v4_fact_first_judgment_schema(
    items: tuple[str, ...] = ITEMS,
) -> dict[str, Any]:
    """Return a one-call observable v4 review followed by model-owned V/E."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["v4검토", "판정"],
        "properties": {
            "v4검토": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "참가자격실적근거", "금액구간", "특정발주기관한정",
                    "특정실적종류한정", "구체적필요사유", "카드대조",
                ],
                "properties": {
                    "참가자격실적근거": {"type": ["string", "null"], "maxLength": 500},
                    "금액구간": {
                        "type": "string", "enum": ["고시금액이상", "고시금액미만", "불명"],
                    },
                    "특정발주기관한정": {
                        "type": "string", "enum": list(V4_PRESENCE_STATES),
                    },
                    "특정실적종류한정": {
                        "type": "string", "enum": list(V4_PRESENCE_STATES),
                    },
                    "구체적필요사유": {
                        "type": "string", "enum": list(V4_PRESENCE_STATES),
                    },
                    "카드대조": {
                        "type": "string", "enum": ["1조건충족", "0조건충족", "판단불가"],
                    },
                },
            },
            "판정": judgment_schema(items=items),
        },
    }


def v4_specialist_fact_first_judgment_schema() -> dict[str, Any]:
    """Return a role-aware v4-only review followed by model-owned v4/e4."""
    items = ("v4",)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["v4역할검토", "판정"],
        "properties": {
            "v4역할검토": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "실적요구원문",
                    "조항역할",
                    "과거계약실적요구",
                    "발주기관범위",
                    "실적종류범위",
                    "유사동등실적인정",
                    "구체적필요사유",
                    "카드대조",
                ],
                "properties": {
                    "실적요구원문": {"type": ["string", "null"], "maxLength": 500},
                    "조항역할": {"type": "string", "enum": list(V4_CLAUSE_ROLES)},
                    "과거계약실적요구": {
                        "type": "string", "enum": list(V4_PRESENCE_STATES),
                    },
                    "발주기관범위": {
                        "type": "string", "enum": list(V4_CLIENT_SCOPES),
                    },
                    "실적종류범위": {
                        "type": "string", "enum": list(V4_PERFORMANCE_SCOPES),
                    },
                    "유사동등실적인정": {
                        "type": "string", "enum": list(V4_PRESENCE_STATES),
                    },
                    "구체적필요사유": {
                        "type": "string", "enum": list(V4_PRESENCE_STATES),
                    },
                    "카드대조": {
                        "type": "string", "enum": ["1조건충족", "0조건충족", "판단불가"],
                    },
                },
            },
            "판정": judgment_schema(items=items),
        },
    }


def v5_numeric_relation_judgment_schema() -> dict[str, Any]:
    """Return a minimal v5 amount/role review followed by model-owned v5/e5."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["v5수치대조", "판정"],
        "properties": {
            "v5수치대조": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "적용분기", "입찰추정가격", "적용임계값", "금액관계",
                    "지역문구역할", "허용사유",
                ],
                "properties": {
                    "적용분기": {
                        "type": "string", "enum": list(V5_THRESHOLD_BRANCHES),
                    },
                    "입찰추정가격": {"type": ["integer", "null"], "minimum": 0},
                    "적용임계값": {"type": ["integer", "null"], "minimum": 0},
                    "금액관계": {
                        "type": "string", "enum": list(V5_AMOUNT_RELATIONS),
                    },
                    "지역문구역할": {
                        "type": "string", "enum": list(V5_REGION_ROLES),
                    },
                    "허용사유": {
                        "type": "string", "enum": list(V4_PRESENCE_STATES),
                    },
                },
            },
            "판정": judgment_schema(items=("v5",)),
        },
    }


def v6_geography_proof_judgment_schema() -> dict[str, Any]:
    """Return observable v6 operands followed by model-owned v6/e6."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["v6지역대조", "판정"],
        "properties": {
            "v6지역대조": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "금액구간", "지역참가자격원문", "지역문구역할",
                    "기초지역참가제한", "계약절차", "허용요건", "카드대조",
                ],
                "properties": {
                    "금액구간": {
                        "type": "string", "enum": ["고시금액미만", "고시금액이상", "불명"],
                    },
                    "지역참가자격원문": {
                        "type": ["string", "null"], "maxLength": 500,
                    },
                    "지역문구역할": {
                        "type": "string", "enum": list(V6_REGION_ROLES),
                    },
                    "기초지역참가제한": {
                        "type": "string", "enum": list(V6_BASIC_REGION_STATES),
                    },
                    "계약절차": {
                        "type": "string", "enum": list(V6_PROCEDURE_STATES),
                    },
                    "허용요건": {
                        "type": "string", "enum": list(V6_EXCEPTION_STATES),
                    },
                    "카드대조": {
                        "type": "string", "enum": ["1조건충족", "0조건충족", "판단불가"],
                    },
                },
            },
            "판정": judgment_schema(items=("v6",)),
        },
    }


def v23_quantitative_proof_judgment_schema(
    output_mode: str = "labels_and_evidence",
) -> dict[str, Any]:
    """Return observable v23 operands followed by a model-owned v23 decision."""
    if output_mode not in {"labels_and_evidence", "labels_only"}:
        raise ValueError("v23 quantitative proof supports only V/E or V-only")
    source_or_null = {"type": ["string", "null"], "maxLength": 500}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["v23기간대조", "판정"],
        "properties": {
            "v23기간대조": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "적용계약법", "계약방식", "입찰추정가격", "금액구간",
                    "적용최소일수", "공고일근거", "종료일근거", "종료일역할",
                    "계산일수", "긴급재공고", "카드대조",
                ],
                "properties": {
                    "적용계약법": {"type": "string", "enum": list(V23_LAW_STATES)},
                    "계약방식": {"type": "string", "enum": list(V23_CONTRACT_STATES)},
                    "입찰추정가격": {"type": ["integer", "null"], "minimum": 0},
                    "금액구간": {"type": "string", "enum": list(V23_AMOUNT_BANDS)},
                    "적용최소일수": {"type": ["integer", "null"], "enum": [10, 20, 40, None]},
                    "공고일근거": source_or_null,
                    "종료일근거": source_or_null,
                    "종료일역할": {"type": "string", "enum": list(V23_DEADLINE_ROLES)},
                    "계산일수": {"type": ["integer", "null"], "minimum": 0},
                    "긴급재공고": {"type": "string", "enum": list(V23_URGENT_STATES)},
                    "카드대조": {
                        "type": "string", "enum": ["1조건충족", "0조건충족", "판단불가"],
                    },
                },
            },
            "판정": judgment_schema(items=("v23",), output_mode=output_mode),
        },
    }


def v19_role_proof_judgment_schema(
    output_mode: str = "labels_and_evidence",
) -> dict[str, Any]:
    """Return observable v19 document/timing roles and a model-owned decision."""
    if output_mode not in {"labels_and_evidence", "labels_only"}:
        raise ValueError("v19 role proof supports only V/E or V-only")
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["v19역할대조", "판정"],
        "properties": {
            "v19역할대조": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "후보원문", "서류종류", "요구행위", "기준시점", "입찰효과", "카드대조",
                ],
                "properties": {
                    "후보원문": {"type": ["string", "null"], "maxLength": 500},
                    "서류종류": {"type": "string", "enum": list(V19_DOCUMENT_KINDS)},
                    "요구행위": {"type": "string", "enum": list(V19_REQUIRED_ACTIONS)},
                    "기준시점": {"type": "string", "enum": list(V19_TIMING_STATES)},
                    "입찰효과": {"type": "string", "enum": list(V19_BID_EFFECTS)},
                    "카드대조": {
                        "type": "string", "enum": ["1조건충족", "0조건충족", "판단불가"],
                    },
                },
            },
            "판정": judgment_schema(items=("v19",), output_mode=output_mode),
        },
    }


def v10_product_presence_judgment_schema() -> dict[str, Any]:
    """Return v10 product/applicability observations and a model-owned label."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["v10제품검토", "판정"],
        "properties": {
            "v10제품검토": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "실제구매대상", "고시후보세부품명", "적용조건상태",
                    "경쟁제품적용", "직접생산요구", "직접생산요구원문",
                ],
                "properties": {
                    "실제구매대상": {"type": ["string", "null"]},
                    "고시후보세부품명": {"type": ["string", "null"]},
                    "적용조건상태": {
                        "type": "string", "enum": list(V10_CONDITION_STATES),
                    },
                    "경쟁제품적용": {
                        "type": "string", "enum": list(V10_APPLICABILITY_STATES),
                    },
                    "직접생산요구": {
                        "type": "string", "enum": list(V10_PRESENCE_STATES),
                    },
                    "직접생산요구원문": {"type": ["string", "null"]},
                },
            },
            "판정": judgment_schema(items=("v10",), output_mode="labels_only"),
        },
    }


def v12_product_target_judgment_schema(
    output_mode: str = "labels_and_evidence",
) -> dict[str, Any]:
    """Return v12 target/product observations and a model-owned judgment."""
    if output_mode not in {"labels_and_evidence", "labels_only"}:
        raise ValueError("v12 product target review supports only V/E or V-only")
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["v12제품대상검토", "판정"],
        "properties": {
            "v12제품대상검토": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "실제구매대상원문", "고시후보세부품명", "고시후보출처",
                    "구매대상관계", "적용조건상태", "경쟁제품적용",
                    "직접생산요구원문", "직접생산요구역할", "허용사유", "카드대조",
                ],
                "properties": {
                    "실제구매대상원문": {"type": ["string", "null"], "maxLength": 500},
                    "고시후보세부품명": {"type": ["string", "null"]},
                    "고시후보출처": {
                        "type": "string", "enum": list(V12_CANDIDATE_SOURCES),
                    },
                    "구매대상관계": {
                        "type": "string", "enum": list(V12_TARGET_RELATIONS),
                    },
                    "적용조건상태": {
                        "type": "string", "enum": list(V10_CONDITION_STATES),
                    },
                    "경쟁제품적용": {
                        "type": "string", "enum": list(V10_APPLICABILITY_STATES),
                    },
                    "직접생산요구원문": {"type": ["string", "null"], "maxLength": 500},
                    "직접생산요구역할": {
                        "type": "string", "enum": list(V12_REQUIREMENT_ROLES),
                    },
                    "허용사유": {
                        "type": "string", "enum": list(V12_EXCEPTION_STATES),
                    },
                    "카드대조": {
                        "type": "string", "enum": ["1조건충족", "0조건충족", "판단불가"],
                    },
                },
            },
            "판정": judgment_schema(items=("v12",), output_mode=output_mode),
        },
    }


def v13_product_scope_judgment_schema() -> dict[str, Any]:
    """Return v13 product/scope observations and a model-owned v13/e13."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["v13제품기업검토", "판정"],
        "properties": {
            "v13제품기업검토": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "실제구매대상", "고시후보세부품명", "적용조건상태",
                    "경쟁제품적용", "기업제한원문", "기업제한역할",
                    "일반중기업참가", "허용사유", "카드대조",
                ],
                "properties": {
                    "실제구매대상": {"type": ["string", "null"]},
                    "고시후보세부품명": {"type": ["string", "null"]},
                    "적용조건상태": {
                        "type": "string", "enum": list(V10_CONDITION_STATES),
                    },
                    "경쟁제품적용": {
                        "type": "string", "enum": list(V10_APPLICABILITY_STATES),
                    },
                    "기업제한원문": {"type": ["string", "null"], "maxLength": 500},
                    "기업제한역할": {
                        "type": "string", "enum": list(V13_CLAUSE_ROLES),
                    },
                    "일반중기업참가": {
                        "type": "string", "enum": list(V13_MEDIUM_BUSINESS_STATES),
                    },
                    "허용사유": {
                        "type": "string", "enum": list(V13_EXCEPTION_STATES),
                    },
                    "카드대조": {
                        "type": "string", "enum": ["1조건충족", "0조건충족", "판단불가"],
                    },
                },
            },
            "판정": judgment_schema(items=("v13",)),
        },
    }


def category_fact_first_judgment_schema(
    items: tuple[str, ...] = ITEMS,
    max_facts_per_category: int = 2,
) -> dict[str, Any]:
    """Return a one-call source-fact inventory followed by model-owned V/E."""
    if max_facts_per_category <= 0:
        raise ValueError("max_facts_per_category must be positive")
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["사실목록", "판정"],
        "properties": {
            "사실목록": {
                "type": "object",
                "additionalProperties": False,
                "required": list(FACT_INVENTORY_CATEGORIES),
                "properties": {
                    category: {
                        "type": "array",
                        "maxItems": max_facts_per_category,
                        "items": {
                            "type": "string", "minLength": 1, "maxLength": 360,
                        },
                    }
                    for category in FACT_INVENTORY_CATEGORIES
                },
            },
            "판정": judgment_schema(items=items),
        },
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
    if categories not in {
        FACT_INVENTORY_CATEGORIES,
        FACT_INVENTORY_CATEGORIES_V2,
        V6_GEOGRAPHY_FACT_FIELDS,
    }:
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


def v23_proof_judgment_schema() -> dict[str, Any]:
    """EXP191's model-owned v23 V/E plus observable source proof fields."""
    source_or_null = {"type": ["string", "null"], "maxLength": 500}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "지방협상_근거", "공고일_근거", "종료일_근거", "종료일_역할",
            "긴급재공고_근거", "판정",
        ],
        "properties": {
            "지방협상_근거": source_or_null,
            "공고일_근거": source_or_null,
            "종료일_근거": source_or_null,
            "종료일_역할": {"type": "string", "enum": ["현장설명회", "제안서마감", "없음"]},
            "긴급재공고_근거": source_or_null,
            "판정": {
                "type": "object", "additionalProperties": False,
                "required": ["위반여부", "근거문구"],
                "properties": {
                    "위반여부": {"type": "integer", "enum": [0, 1]},
                    "근거문구": {"type": ["string", "null"], "maxLength": 2000},
                },
            },
        },
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
