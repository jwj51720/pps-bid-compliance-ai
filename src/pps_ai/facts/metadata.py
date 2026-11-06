"""Item-scoped, human-readable organizer metadata facts without legal decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any, Mapping, Sequence


FIELD_LABELS = {
    "적용계약법": "적용 계약법 입력",
    "업무구분": "조달 업무구분 입력",
    "계약방법": "계약 경쟁방식 입력",
    "낙찰방법": "낙찰방식 입력",
    "소관구분": "소관 기관구분 입력",
    "입찰추정가격": "입찰추정가격 입력",
    "배정예산금액": "배정예산금액 입력",
    "공동도급구성방식": "공동도급 구성방식 입력",
    "정보화사업여부": "정보화사업 여부 입력",
    "공고게시일자": "공고 게시일 입력",
    "긴급공고여부": "긴급공고 여부 입력",
    "지역제한여부": "지역제한 여부 입력",
    "제한지역코드목록": "제한지역 입력",
    "업종제한여부": "업종제한 여부 입력",
    "면허업종제한목록": "제한 업종 입력",
    "조항호내용": "전자조달 기재 조항 내용",
}

ITEM_METADATA_FIELDS: dict[str, tuple[str, ...]] = {
    "v1": (),
    "v2": ("적용계약법", "업무구분", "소관구분", "입찰추정가격", "계약방법", "낙찰방법"),
    "v3": ("적용계약법", "업무구분", "입찰추정가격"),
    "v4": ("적용계약법", "입찰추정가격"),
    "v5": ("적용계약법", "업무구분", "소관구분", "입찰추정가격", "계약방법", "지역제한여부", "제한지역코드목록"),
    "v6": ("적용계약법", "업무구분", "소관구분", "입찰추정가격", "계약방법", "낙찰방법", "지역제한여부", "제한지역코드목록"),
    "v7": ("적용계약법", "업무구분", "소관구분", "입찰추정가격", "계약방법", "낙찰방법", "지역제한여부", "제한지역코드목록"),
    "v8": ("적용계약법", "계약방법", "낙찰방법", "입찰추정가격", "지역제한여부", "제한지역코드목록"),
    "v9": ("적용계약법",),
    "v10": ("업무구분", "계약방법", "입찰추정가격", "조항호내용"),
    "v11": ("업무구분", "계약방법", "입찰추정가격", "조항호내용"),
    "v12": ("업무구분", "계약방법", "입찰추정가격", "조항호내용"),
    "v13": ("업무구분", "계약방법", "입찰추정가격", "조항호내용"),
    "v14": ("업무구분", "계약방법", "입찰추정가격", "조항호내용"),
    "v15": ("업무구분", "계약방법", "입찰추정가격", "조항호내용"),
    "v16": ("업무구분", "계약방법", "입찰추정가격", "조항호내용"),
    "v17": ("업무구분", "계약방법", "입찰추정가격", "조항호내용"),
    "v18": ("업무구분", "계약방법", "입찰추정가격", "조항호내용"),
    "v19": (),
    "v20": ("업무구분", "입찰추정가격", "정보화사업여부", "조항호내용"),
    "v21": ("적용계약법", "업무구분", "입찰추정가격", "공동도급구성방식"),
    "v22": ("낙찰방법",),
    "v23": ("적용계약법", "낙찰방법", "입찰추정가격", "공고게시일자", "긴급공고여부"),
    "v24": ("배정예산금액", "입찰추정가격", "계약방법", "낙찰방법", "지역제한여부", "제한지역코드목록", "업종제한여부", "면허업종제한목록"),
}

FLAG_FIELDS = {"정보화사업여부", "긴급공고여부", "지역제한여부", "업종제한여부"}
MONEY_FIELDS = {"입찰추정가격", "배정예산금액"}
DATE_FIELDS = {"공고게시일자"}
REGISTERED_REGION = re.compile(
    r"\[등록지역:r[0-9]+\|단위=(기초|광역)\|광역=([^\]]+)\]"
)
INDUSTRY_CODE = re.compile(r"\(([0-9]{4})\)")


@dataclass(frozen=True)
class MetadataFact:
    source_field: str
    label: str
    rendered_value: str
    available: bool


def _region_text(value: str) -> str:
    if "[등록지역:" not in value:
        if "[" in value or "]" in value:
            raise ValueError("unknown region metadata syntax")
        return value
    parts: list[str] = []
    for part in value.split(", "):
        match = REGISTERED_REGION.fullmatch(part.strip())
        if match is None:
            raise ValueError("unknown registered-region metadata syntax")
        level, province = match.groups()
        if level == "기초":
            parts.append(f"{province} 관할 기초지역(세부 시군구 미제공)")
        else:
            parts.append(f"{province} 광역지역")
    return ", ".join(parts)


def _format_value(field: str, value: Any) -> tuple[str, bool]:
    if value is None or value == "" or value == "미입력":
        return "확인되지 않음", False
    if field in MONEY_FIELDS:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{field}: expected nonnegative integer won")
        return f"{value:,}원", True
    if not isinstance(value, str):
        raise ValueError(f"{field}: expected text")
    if field in FLAG_FIELDS:
        if value not in {"Y", "N"}:
            raise ValueError(f"{field}: unknown flag")
        return ("예" if value == "Y" else "아니오"), True
    if field in DATE_FIELDS:
        if not re.fullmatch(r"[0-9]{8}", value):
            raise ValueError(f"{field}: unknown date format")
        date = datetime.strptime(value, "%Y%m%d")
        return date.strftime("%Y-%m-%d"), True
    if field == "제한지역코드목록":
        return _region_text(value), True
    if field == "면허업종제한목록":
        return INDUSTRY_CODE.sub(
            lambda match: f" [업종식별번호 {match.group(1)}]", value
        ), True
    if field == "조항호내용" and len(value) > 1000:
        raise ValueError("organizer clause content unexpectedly long")
    if "{" in value or "}" in value:
        raise ValueError(f"{field}: raw object-like text is not renderable")
    return value, True


def build_metadata_facts(
    metadata: Mapping[str, Any], item_ids: Sequence[str],
) -> tuple[MetadataFact, ...]:
    requested: set[str] = set()
    for item_id in item_ids:
        if item_id not in ITEM_METADATA_FIELDS:
            raise ValueError(f"unknown item: {item_id}")
        requested.update(ITEM_METADATA_FIELDS[item_id])
    facts: list[MetadataFact] = []
    for field, label in FIELD_LABELS.items():
        if field not in requested:
            continue
        if field not in metadata:
            raise ValueError(f"organizer metadata field missing: {field}")
        rendered, available = _format_value(field, metadata[field])
        facts.append(MetadataFact(field, label, rendered, available))
    return tuple(facts)


def render_metadata_facts(facts: Sequence[MetadataFact]) -> str:
    if not facts:
        return ""
    lines = [
        "주최측 전자조달 입력 사실(공고 원문과 별도로 대조하며, 이 값만으로 위반을 확정하지 않음):"
    ]
    lines.extend(f"- {fact.label}: {fact.rendered_value}" for fact in facts)
    return "\n".join(lines)
