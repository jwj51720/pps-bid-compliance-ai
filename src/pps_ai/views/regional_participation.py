"""Exact source candidates for bidder-location participation restrictions."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping


LOCATION_ROLE = re.compile(
    r"주된\s*(?:영업소|사무소)|본\s*점\s*(?:소재지)?|본사\s*(?:소재지)?|"
    r"(?:사업장|영업장)의?\s*소재지"
)
RESTRICTION_ROLE = re.compile(
    r"업체|입찰참가자|참가자격을\s*갖춘\s*자|"
    r"업체이어야|업체여야|업체로\s*제한|자에\s*한함|자이어야|자여야"
)
LOCATION_LINK = re.compile(
    r"(?:둔|두고|두어야|소재한|소재하는|소재하고|소재하여|"
    r"소재해야|위치한|등록된|기재되어\s*있는|한정한다|제한한다)|"
    r"소재지\s*\)|소재지\s*가|있는\s*업체"
)
NEGATIVE_ROLE = re.compile(
    r"가점|배점|평가항목|운반거리|납품장소|배출현장|"
    r"하도급\s*업체를|최대한\s*이용|우대점수"
)
REGION_VALUE = re.compile(
    r"\[지역:[^]]+\]|서울특별시|부산광역시|대구광역시|인천광역시|"
    r"광주광역시|대전광역시|울산광역시|세종특별자치시|경기도|"
    r"강원특별자치도|충청북도|충청남도|전북특별자치도|"
    r"전라남도|경상북도|경상남도|제주특별자치도|"
    r"서울시|부산시|대구시|인천시|광주시|대전시|울산시|"
    r"경북|경남|전북|전남|충북|충남"
)
BASIC_REGION = re.compile(r"\[지역:[^]]*단위=기초[^]]*\]")


@dataclass(frozen=True)
class RegionalParticipationCandidate:
    doc_id: str
    document_type: str
    document_order: int
    start: int
    end: int
    exact_text: str
    basic_region: bool
    region_count: int


def _clause_windows(text: str) -> tuple[tuple[int, int], ...]:
    """Use single source lines, joining only a wrapped immediate continuation."""
    lines = text.splitlines(keepends=True)
    offsets: list[int] = []
    cursor = 0
    for line in lines:
        offsets.append(cursor)
        cursor += len(line)
    windows: list[tuple[int, int]] = []
    for index, line in enumerate(lines):
        if not LOCATION_ROLE.search(line) and not (
            REGION_VALUE.search(line) and "소재한" in line and "업체" in line
        ):
            continue
        start = offsets[index]
        end = start + len(line)
        if index + 1 < len(lines) and len(line) < 240:
            end += len(lines[index + 1])
        windows.append((start, end))
    return tuple(windows)


def build_regional_participation_candidates(
    record: Mapping[str, Any],
) -> tuple[RegionalParticipationCandidate, ...]:
    candidates: list[RegionalParticipationCandidate] = []
    for order, document in enumerate(record.get("docs") or []):
        text = document.get("text")
        if not isinstance(text, str):
            continue
        for start, end in _clause_windows(text):
            raw = text[start:end]
            leading = len(raw) - len(raw.lstrip())
            trailing = len(raw) - len(raw.rstrip())
            start += leading
            end -= trailing
            clause = text[start:end]
            has_location_role = bool(LOCATION_ROLE.search(clause))
            has_direct_region_role = bool(
                REGION_VALUE.search(clause)
                and re.search(r"소재한\s*[^\n]{0,80}업체", clause)
                and re.search(r"입찰|응모|참가자격|자격", text[max(0, start - 1000):start])
            )
            if not has_location_role and not has_direct_region_role:
                continue
            if not RESTRICTION_ROLE.search(clause):
                continue
            if not LOCATION_LINK.search(clause):
                continue
            region_match = REGION_VALUE.search(clause)
            if region_match is None:
                continue
            if NEGATIVE_ROLE.search(clause):
                continue
            if len(clause) > 500:
                location = LOCATION_ROLE.search(clause)
                anchor = min(
                    location.start() if location is not None else region_match.start(),
                    region_match.start(),
                )
                start += max(0, anchor - 50)
                end = min(end, start + 500)
            exact = text[start:end]
            candidates.append(RegionalParticipationCandidate(
                doc_id=str(document.get("doc_id") or ""),
                document_type=str(document.get("type") or ""),
                document_order=order,
                start=start,
                end=end,
                exact_text=exact,
                basic_region=bool(BASIC_REGION.search(clause)),
                region_count=len(REGION_VALUE.findall(clause)),
            ))
    return tuple(candidates)
