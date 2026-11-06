from __future__ import annotations

from src.pps_ai.decisions.v19_compact_serialization import adapt_compact_response
from src.pps_ai.v19_compact_probe import _compact_mock_response
from src.pps_ai.views.v19_requirements import build_v19_requirement_view
from src.pps_ai.decisions.v19_compact_serialization import build_v19_compact_task


def test_compact_probe_mock_satisfies_adapter_for_every_candidate() -> None:
    record = {
        "id": "N1",
        "meta": {},
        "docs": [{
            "doc_id": "D0",
            "type": "공고문",
            "text": "제조사 물품공급 확약서와 공급사 기술지원 확약서를 제출한다.",
        }],
    }
    candidates = build_v19_requirement_view(record)["candidates"]
    task = build_v19_compact_task(record, candidates)
    response = _compact_mock_response(task)
    adapted = adapt_compact_response(response, candidates)
    assert adapted is not None
    assert response["finish_reason"] == "stop"
    assert set(task["schema"]["properties"]["observations"]["required"]) == {
        candidate.source_id for candidate in candidates
    }
