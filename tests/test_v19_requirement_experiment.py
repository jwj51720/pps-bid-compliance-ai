from __future__ import annotations

from types import SimpleNamespace

from src.pps_ai.v19_requirement_experiment import V19RequirementExperiment
from src.pps_ai.views.v19_requirements import build_v19_requirement_view


class _CandidateCountCounter:
    def count(self, messages: list[dict[str, str]]) -> int:
        user = messages[1]["content"]
        return 100 * sum(f"[R{index:02d} |" in user for index in range(1, 20))


def test_token_packing_splits_without_dropping_or_reordering_candidates() -> None:
    record = {
        "id": "N1",
        "meta": {},
        "docs": [{
            "doc_id": "D0",
            "type": "공고문",
            "text": "\n".join([
                "제조사 물품공급 확약서 첫 번째 요구",
                "X" * 1600,
                "공급사 기술지원 확약서 두 번째 요구",
                "Y" * 1600,
                "입찰자 직접이행 확약서 세 번째 요구",
            ]),
        }],
    }
    candidates = build_v19_requirement_view(record)["candidates"]
    assert [candidate.source_id for candidate in candidates] == ["R01", "R02", "R03"]
    experiment = object.__new__(V19RequirementExperiment)
    experiment.config = SimpleNamespace(prompt_budget=200)
    experiment.counter = _CandidateCountCounter()
    packs = experiment._pack_tasks(record, candidates)
    assert [[candidate.source_id for candidate in pack[0]] for pack in packs] == [
        ["R01", "R02"], ["R03"],
    ]
    assert all(tokens <= 200 for _, _, tokens in packs)
