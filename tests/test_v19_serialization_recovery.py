from __future__ import annotations

import json
from types import SimpleNamespace

from src.pps_ai.decisions.v19_requirements import build_v19_task
from src.pps_ai.v19_serialization_recovery import (
    V19SerializationRecovery,
    invalid_v19_task_ids,
)
from src.pps_ai.views.v19_requirements import build_v19_requirement_view


def _fixture() -> tuple[SimpleNamespace, dict[str, object], tuple[object, ...]]:
    raw = {
        "id": "N1",
        "meta": {},
        "docs": [{
            "doc_id": "D0",
            "type": "공고문",
            "text": "제조사 물품공급 확약서를 계약 시 제출한다.",
        }],
    }
    record = SimpleNamespace(notice_id="N1", raw=raw)
    candidates = tuple(build_v19_requirement_view(raw)["candidates"])
    return record, raw, candidates


def _verbose_response(candidates: tuple[object, ...]) -> dict[str, object]:
    return {
        "finish_reason": "stop",
        "invalid": False,
        "content": json.dumps({
            "observations": {
                candidate.source_id: {
                    "requirement_role": "CONTRACT_PERFORMANCE",
                    "document_kind": "EXTERNAL_SUPPLY_OR_TECH_ASSURANCE",
                    "external_issuer_explicit": "YES",
                    "bidder_must_obtain_or_hold": "NO",
                    "bidder_must_submit": "YES",
                    "obtain_before_bid_deadline": "NO",
                    "submit_with_bid_or_proposal": "NO",
                    "submit_after_bid_or_contract": "YES",
                    "quoted_text": candidate.text,
                }
                for candidate in candidates
            }
        }, ensure_ascii=False),
    }


def test_valid_primary_response_selects_no_recovery_task() -> None:
    _, _, candidates = _fixture()
    responses = {"N1__p01": _verbose_response(candidates)}
    assert invalid_v19_task_ids(responses, {"N1__p01": candidates}) == []


def test_invalid_primary_gets_one_isomorphic_compact_recovery(tmp_path) -> None:
    record, raw, candidates = _fixture()
    primary = build_v19_task(raw, candidates)
    calls = []

    def complete(task: dict[str, object]) -> dict[str, object]:
        calls.append(task)
        return {
            "finish_reason": "stop",
            "invalid": False,
            "content": json.dumps({
                "observations": {
                    candidate.source_id: {
                        "r": 2, "k": 0, "x": 1, "h": 0, "s": 1,
                        "b": 0, "w": 0, "a": 1, "q": candidate.text,
                    }
                    for candidate in candidates
                }
            }, ensure_ascii=False),
        }

    config = SimpleNamespace(
        raw={
            "v19_serialization_recovery": {
                "module": "v19-invalid-only-compact-recovery-v1",
                "max_retries_per_invalid_task": 1,
            }
        },
        tokenizer_dir="unused",
        prompt_budget=14848,
    )
    recovery = object.__new__(V19SerializationRecovery)
    recovery.config = config
    recovery.output_dir = tmp_path
    recovery.counter = SimpleNamespace(count=lambda messages: 100)
    effective, report = recovery.apply(
        records=[record],
        primary_tasks={"N1__p01": primary},
        task_candidates={"N1__p01": candidates},
        responses={
            "N1__p01": {
                "finish_reason": "length", "invalid": False, "content": "{",
            }
        },
        complete=complete,
    )
    assert len(calls) == 1
    assert calls[0]["messages"][1] == primary["messages"][1]
    assert calls[0]["messages"][0]["content"].startswith(
        primary["messages"][0]["content"]
    )
    assert report["primary_invalid_tasks"] == 1
    assert report["invalid_after_recovery"] == 0
    assert effective["N1__p01"]["finish_reason"] == "stop"
