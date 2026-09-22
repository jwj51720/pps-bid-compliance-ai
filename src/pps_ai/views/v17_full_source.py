"""V17-specific full-source observation task for zero-call admission review."""

from __future__ import annotations

from typing import Any, Mapping

from ..domain.models import NoticeRecord
from ..facts.document_product_codes import (
    collect_document_product_mentions, render_document_product_mentions,
)
from ..facts.metadata import build_metadata_facts, render_metadata_facts
from ..facts.product_codes import build_product_facts, render_product_facts
from .native_full_prompt import DOCUMENT_ORDER
from .v17_relation_view import V17RelationView, render_v17_relation_view


SYSTEM_MESSAGE = """공고의 v17 판단에 필요한 사실만 세 축으로 관측한다.
최종 위반 라벨은 출력하지 않는다. 먼저 실제 구매대상 물품·용역을 확인하고,
그 대상에 경쟁제품 CSV 행과 특이사항이 적용되는지 원문과 대조한다.
직접생산확인서나 등록 참가자격에만 붙은 품명번호를 구매대상으로 바꾸지 않는다.
메타데이터 코드가 없거나 CSV 행이 없다는 것만으로 일반제품임을 확정하지 않는다.
다음으로 중기업까지 참가 가능한지 소기업·소상공인만 가능한지 실제 참가조건을
구분한다. 확인서의 명칭만으로 기업범위를 결정하지 않는다. 끝으로 유찰,
자격업체 부족, 비영리법인 등 예외가 이번 구매에 실제 적용되는지 확인한다.
알 수 없는 축은 U로 남긴다. 서로 다른 문서의 조건을 같은 조건인 것처럼
결합하지 않는다.

product: G=실제 구매대상이 적용 경쟁제품이 아님이 확인됨,
C=실제 구매대상이 CSV 경쟁제품 행·특이사항에 적용됨, U=둘 다 미확인.
enterprise: M=중기업도 실제 참가 가능, S=일반 영리기업은 소기업·소상공인만
가능, N=기업규모 참가제한 없음, U=역할 또는 범위 불명.
exception: Y=중기업 허용 또는 우선조달 생략의 법정 예외가 이번 계약에
실제 적용, N=그런 적용 예외가 공고 자료에 확인되지 않음, U=불명.
quote: enterprise=M인 경우 그 실제 참가자격을 직접 보여주는 제공 문서
원문의 연속된 1~500자를 복사한다. 그 외에는 null이다.
JSON 이외에는 출력하지 않는다."""


def eligible_v17_full_source(record: NoticeRecord) -> bool:
    price = record.metadata.get("입찰추정가격")
    business = record.metadata.get("업무구분")
    if isinstance(price, bool) or not isinstance(price, int) or price < 0:
        raise ValueError(f"{record.notice_id}: valid estimated price required")
    if not isinstance(business, str):
        raise ValueError(f"{record.notice_id}: business type required")
    return price < 100_000_000 and ("물품" in business or "용역" in business)


def build_v17_full_source_task(
    record: NoticeRecord,
    card_text: str,
    product_index: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    if not eligible_v17_full_source(record):
        raise ValueError(f"{record.notice_id}: v17 applicability gate failed")
    if not card_text.strip():
        raise ValueError("v17 card text required")
    metadata = render_metadata_facts(build_metadata_facts(record.metadata, ("v17",)))
    meta_products = render_product_facts(build_product_facts(record.metadata, product_index))
    document_products = render_document_product_mentions(
        collect_document_product_mentions(record, product_index)
    )
    unknown_types = {
        document.document_type for document in record.documents
    } - set(DOCUMENT_ORDER)
    if unknown_types:
        raise ValueError(f"unknown document types: {sorted(unknown_types)}")
    document_text = "\n\n".join(
        f"[{document.document_type}/{document.doc_id}]\n{document.text}"
        for document in sorted(
            record.documents,
            key=lambda document: (
                DOCUMENT_ORDER[document.document_type], document.order,
            ),
        )
    )
    user_message = (
        f"[공고] {record.notice_id}\n\n"
        f"[v17 판정 계약]\n{card_text}\n\n"
        f"[전자조달 입력 사실]\n{metadata}\n\n"
        f"[metadata 제품코드의 CSV 대조]\n{meta_products}\n\n"
        f"[문서 제품코드의 CSV 대조와 원문 문맥]\n{document_products}\n\n"
        f"[모든 제공 문서 원문]\n{document_text}"
    )
    return {
        "id": record.notice_id,
        "arm": "NATIVE_V17_FULL_SOURCE_OBSERVATION_V1",
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": user_message},
        ],
        "schema": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "product": {"type": "string", "enum": ["G", "C", "U"]},
                "enterprise": {"type": "string", "enum": ["M", "S", "N", "U"]},
                "exception": {"type": "string", "enum": ["Y", "N", "U"]},
                "quote": {"type": ["string", "null"], "maxLength": 500},
            },
            "required": ["product", "enterprise", "exception", "quote"],
        },
    }


def build_v17_relation_task(
    record: NoticeRecord,
    card_text: str,
    product_index: Mapping[str, Mapping[str, str]],
    view: V17RelationView,
) -> dict[str, Any]:
    if view.notice_id != record.notice_id:
        raise ValueError("v17 relation view identity mismatch")
    if {row["doc_id"] for row in view.document_coverage} != {
        document.doc_id for document in record.documents
    }:
        raise ValueError("v17 relation view omits a document")
    task = build_v17_full_source_task(record, card_text, product_index)
    marker = "[모든 제공 문서 원문]"
    user = task["messages"][1]["content"]
    if user.count(marker) != 1:
        raise ValueError("v17 full-source marker mismatch")
    prefix = user.split(marker, 1)[0]
    task["messages"][0]["content"] += (
        "\n아래 원문 조각은 모든 문서를 검사해 찾은 부분일 뿐이다. "
        "보이지 않는 원문의 사실이 없다고 추정하지 않는다."
    )
    task["messages"][1]["content"] = (
        prefix + "[모든 문서의 source-grounded 관계 단서]\n"
        + render_v17_relation_view(view)
    )
    if view.version not in {"v1", "v2", "v3"}:
        raise ValueError(f"unknown v17 relation view: {view.version}")
    task["arm"] = f"NATIVE_V17_RELATION_VIEW_OBSERVATION_{view.version.upper()}"
    return task
