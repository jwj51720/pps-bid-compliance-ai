"""Source-grounded exact product-code mentions from every notice document."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping

from ..domain.models import NoticeRecord, SourceSpan


TEN_DIGIT_CODE = re.compile(r"(?<![0-9])[0-9]{10}(?![0-9])")
CONTEXT_CHARS = 100


@dataclass(frozen=True)
class DocumentProductMention:
    code: str
    code_span: SourceSpan
    context_span: SourceSpan
    csv_name: str | None
    special_note: str | None


def collect_document_product_mentions(
    record: NoticeRecord,
    product_index: Mapping[str, Mapping[str, str]],
) -> tuple[DocumentProductMention, ...]:
    """Find all code-shaped source facts without deciding the code's role."""
    mentions: list[DocumentProductMention] = []
    for document in record.documents:
        for match in TEN_DIGIT_CODE.finditer(document.text):
            code = match.group()
            context_start = max(0, match.start() - CONTEXT_CHARS)
            context_end = min(len(document.text), match.end() + CONTEXT_CHARS)
            code_span = SourceSpan(
                record.notice_id, document.doc_id, document.document_type,
                document.order, match.start(), match.end(), code, document.sha256,
            )
            context_span = SourceSpan(
                record.notice_id, document.doc_id, document.document_type,
                document.order, context_start, context_end,
                document.text[context_start:context_end], document.sha256,
            )
            code_span.validate(document)
            context_span.validate(document)
            csv_row = product_index.get(code)
            mentions.append(DocumentProductMention(
                code=code,
                code_span=code_span,
                context_span=context_span,
                csv_name=csv_row["세부품명"] if csv_row is not None else None,
                special_note=(csv_row.get("특이사항") or None)
                if csv_row is not None else None,
            ))
    return tuple(mentions)


def render_document_product_mentions(
    mentions: tuple[DocumentProductMention, ...],
) -> str:
    if not mentions:
        return "제공 문서에서 독립된 10자리 제품코드 표기를 찾지 못했습니다."
    lines = [
        "제공 문서에 적힌 10자리 제품코드 후보(구매대상인지 참가자격용인지 별도 확인 필요):"
    ]
    for mention in mentions:
        source = mention.code_span
        csv_fact = (
            f"주최측 경쟁제품 CSV의 세부품명 {mention.csv_name}과 코드가 정확히 일치"
            if mention.csv_name is not None
            else "주최측 경쟁제품 CSV에 정확히 일치하는 코드 행 없음"
        )
        line = (
            f"- {source.document_type}/{source.document_id} {source.start}:{source.end}의 "
            f"제품코드 {mention.code}: {csv_fact}. "
            f"주변 원문: {mention.context_span.exact_text}"
        )
        if mention.special_note:
            line += f" CSV 특이사항 원문: {mention.special_note}"
        lines.append(line)
    return "\n".join(lines)
