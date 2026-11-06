"""Organizer-sourced regional-restriction threshold facts for v5-v7.

This module classifies only facts that are explicit in organizer metadata or in
the supplied notice documents.  It does not decide whether a regional clause is
a violation; the v5-v7 source predicates remain separate owners.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Mapping, Sequence


LOCAL_PROVINCE_GOODS_GENERAL_SERVICES = 350_000_000
LOCAL_BASIC_EDUCATION_ENTERPRISE = 500_000_000
LOCAL_TECHNICAL_SERVICES = 330_000_000
LOCAL_SAFETY_INSPECTION = 150_000_000

LOCAL_LAW = "지방계약법"
NATIONAL_LAW = "국가계약법"

BASIC_GOVERNMENT_MARKERS = ("기초자치단체",)
PROVINCE_MARKERS = ("광역자치단체",)

INSTITUTION_MARKER = re.compile(r"\[수요기관\(([^)|]+)\)(?:\|[^]]+)?\]")
ISSUER_MARKER = re.compile(
    r"\[수요기관\(([^)|]+)\)(?:\|[^]]+)?\]\s*"
    r"(?:재무|전자입찰|입찰|용역|물품구매|물품)?\s*공고"
)
NAMED_PROVINCE_ISSUER = re.compile(
    r"(서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|"
    r"대전광역시|울산광역시|세종특별자치시|경기도|강원특별자치도|"
    r"충청북도|충청남도|전북특별자치도|전라남도|경상북도|경상남도|"
    r"제주특별자치도)\s*(?:재무|입찰)?\s*공고"
)
NAMED_PROVINCES = frozenset((
    "서울특별시", "부산광역시", "대구광역시", "인천광역시",
    "광주광역시", "대전광역시", "울산광역시", "세종특별자치시",
    "경기도", "강원특별자치도", "충청북도", "충청남도",
    "전북특별자치도", "전라남도", "경상북도", "경상남도",
    "제주특별자치도",
))
TITLE_PREFIX = re.compile(
    r"(?:용\s*역\s*명|공\s*고\s*명|건\s*명|입\s*찰\s*(?:건명|명)|"
    r"사\s*업\s*명|과\s*업\s*명)\s*[:：]?\s*(.+)"
)
SAFETY_SERVICE = re.compile(r"안전\s*점검|정밀\s*안전\s*진단")
TECHNICAL_SERVICE = re.compile(
    r"건설\s*기술|엔지니어링\s*(?:기술|용역|사업)|"
    r"(?:기본|실시|건축|건설|토목|공사|시설)?\s*설계\s*용역|"
    r"(?:건축|건설|토목|공사|시설)[^\n]{0,30}(?:설계|감리)\s*용역|"
    r"(?:설계|감리)\s*용역[^\n]{0,30}(?:건축|건설|토목|공사|시설)"
)


@dataclass(frozen=True)
class FactSource:
    kind: str
    source_name: str
    exact_value: str


@dataclass(frozen=True)
class RegionalThresholdFact:
    notice_id: str
    state: str
    contract_law: str
    procurement_type: str
    service_type: str
    institution_type: str
    threshold_won: int | None
    reason: str
    sources: tuple[FactSource, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _document_texts(record: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    values = []
    for document in record.get("docs") or []:
        text = document.get("text")
        if not isinstance(text, str):
            continue
        values.append((
            str(document.get("doc_id") or ""),
            str(document.get("type") or ""),
            text,
        ))
    return values


def _institution_markers(
    record: Mapping[str, Any],
) -> tuple[set[str], tuple[FactSource, ...]]:
    markers: set[str] = set()
    sources: list[FactSource] = []
    for doc_id, document_type, text in _document_texts(record):
        for match in INSTITUTION_MARKER.finditer(text):
            marker = match.group(1)
            if marker in markers:
                continue
            markers.add(marker)
            sources.append(FactSource(
                kind="document_marker",
                source_name=f"{document_type}:{doc_id}",
                exact_value=match.group(0),
            ))
    return markers, tuple(sources)


def _issuer_sources(record: Mapping[str, Any]) -> tuple[tuple[str, FactSource], ...]:
    """Only header/issuer roles count; incidental body references do not."""
    values: list[tuple[str, FactSource]] = []
    for doc_id, document_type, text in _document_texts(record):
        if document_type != "공고문":
            continue
        header = text[:2500]
        for match in ISSUER_MARKER.finditer(header):
            values.append((
                match.group(1),
                FactSource("issuer_header", f"{document_type}:{doc_id}", match.group(0)),
            ))
        for match in NAMED_PROVINCE_ISSUER.finditer(header):
            values.append((
                match.group(1),
                FactSource("issuer_header", f"{document_type}:{doc_id}", match.group(0)),
            ))
    return tuple(values)


def _title_lines(record: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    """Return exact title-like source lines without assigning a service class."""
    values: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for doc_id, document_type, text in _document_texts(record):
        if document_type != "공고문":
            continue
        for raw_line in text.splitlines()[:160]:
            line = raw_line.strip()
            if not line:
                continue
            match = TITLE_PREFIX.search(line)
            if match is None:
                continue
            exact = match.group(0).strip()
            key = (doc_id, exact)
            if key not in seen:
                seen.add(key)
                values.append(key)
    return tuple(values)


def _service_type(
    record: Mapping[str, Any], procurement_type: str,
) -> tuple[str, tuple[FactSource, ...]]:
    if procurement_type == "goods":
        return "goods_or_general_services", ()
    if procurement_type != "general_services":
        return "not_applicable", ()
    titles = _title_lines(record)
    safety = [value for value in titles if SAFETY_SERVICE.search(value[1])]
    if safety:
        return "safety_inspection_or_precision_diagnosis", tuple(
            FactSource("document_title", doc_id, exact) for doc_id, exact in safety
        )
    technical = [value for value in titles if TECHNICAL_SERVICE.search(value[1])]
    if technical:
        return "technical_design_supervision_engineering", tuple(
            FactSource("document_title", doc_id, exact) for doc_id, exact in technical
        )
    return "goods_or_general_services", ()


def _contains_marker(markers: set[str], needles: Sequence[str]) -> bool:
    return any(any(needle in marker for needle in needles) for marker in markers)


def _institution_type(
    record: Mapping[str, Any], markers: set[str], marker_sources: tuple[FactSource, ...],
) -> tuple[str, tuple[FactSource, ...], str]:
    meta = record.get("meta") or {}
    category = meta.get("소관구분")
    category_source = (
        FactSource("metadata", "소관구분", str(category)),
    ) if isinstance(category, str) and category else ()

    if category == "교육기관":
        return "education_or_school", category_source, "explicit education metadata"
    if category == "지방공기업":
        return "local_public_enterprise", category_source, "explicit local-enterprise metadata"
    issuer = _issuer_sources(record)
    issuer_kinds = {kind for kind, _ in issuer}
    issuer_sources = tuple(source for _, source in issuer)
    basic = _contains_marker(issuer_kinds, BASIC_GOVERNMENT_MARKERS)
    province = _contains_marker(issuer_kinds, PROVINCE_MARKERS)
    named_provinces = issuer_kinds & NAMED_PROVINCES
    if basic and (province or named_provinces):
        return "unknown", category_source + issuer_sources, "conflicting issuer levels"
    if basic:
        return "city_county_district", category_source + issuer_sources, "basic-government issuer header"
    if "세종특별자치시" in issuer_kinds:
        return "sejong", category_source + issuer_sources, "Sejong issuer header"
    if named_provinces:
        if len(named_provinces) != 1:
            return "unknown", category_source + issuer_sources, "multiple province issuer names"
        return "province_except_sejong", category_source + issuer_sources, "named province issuer header"
    if province:
        return (
            "province_or_sejong_unknown",
            category_source + issuer_sources,
            "province issuer marker does not identify Sejong",
        )
    return "unknown", category_source + marker_sources, "no decisive organizer issuer source"


def classify_regional_threshold(record: Mapping[str, Any]) -> RegionalThresholdFact:
    notice_id = str(record.get("id") or "")
    meta = record.get("meta") or {}
    law = str(meta.get("적용계약법") or "")
    procurement = str(meta.get("업무구분") or "")
    base_sources = (
        FactSource("metadata", "적용계약법", law),
        FactSource("metadata", "업무구분", procurement),
    )
    if "공사" in procurement:
        return RegionalThresholdFact(
            notice_id, "NOT_APPLICABLE", law, "construction", "not_applicable",
            "not_applicable", None, "construction thresholds are outside this organizer correction",
            base_sources,
        )
    if procurement == "물품(내자)":
        procurement_type = "goods"
    elif procurement == "일반용역":
        procurement_type = "general_services"
    else:
        return RegionalThresholdFact(
            notice_id, "UNKNOWN", law, "unknown", "unknown", "unknown", None,
            "procurement type is not an exact covered organizer value", base_sources,
        )
    if law == NATIONAL_LAW:
        return RegionalThresholdFact(
            notice_id, "NOT_APPLICABLE", law, procurement_type, "not_applicable",
            "national", None,
            "organizer correction is local-contract-only; preserve national owner", base_sources,
        )
    if law != LOCAL_LAW:
        return RegionalThresholdFact(
            notice_id, "UNKNOWN", law, procurement_type, "unknown", "unknown", None,
            "contract law is not an exact supported organizer value", base_sources,
        )

    service_type, service_sources = _service_type(record, procurement_type)
    if service_type == "safety_inspection_or_precision_diagnosis":
        return RegionalThresholdFact(
            notice_id, "CONFIRMED", law, procurement_type, service_type,
            "service_type_overrides_institution", LOCAL_SAFETY_INSPECTION,
            "explicit service title selects the 150 million won branch",
            base_sources + service_sources,
        )
    if service_type == "technical_design_supervision_engineering":
        return RegionalThresholdFact(
            notice_id, "CONFIRMED", law, procurement_type, service_type,
            "service_type_overrides_institution", LOCAL_TECHNICAL_SERVICES,
            "explicit service title selects the 330 million won branch",
            base_sources + service_sources,
        )

    markers, marker_sources = _institution_markers(record)
    institution, institution_sources, reason = _institution_type(
        record, markers, marker_sources,
    )
    if institution in {"education_or_school", "local_public_enterprise", "city_county_district", "sejong"}:
        threshold = LOCAL_BASIC_EDUCATION_ENTERPRISE
        state = "CONFIRMED"
    elif institution == "province_except_sejong":
        threshold = LOCAL_PROVINCE_GOODS_GENERAL_SERVICES
        state = "CONFIRMED"
    else:
        threshold = None
        state = "UNKNOWN"
    return RegionalThresholdFact(
        notice_id, state, law, procurement_type, service_type, institution,
        threshold, reason, base_sources + service_sources + institution_sources,
    )
