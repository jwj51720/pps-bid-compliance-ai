from src.pps_ai.v5_role_guard_diagnostic import frozen_v5_positive


class _Hits:
    @staticmethod
    def strict_region_hits(record):
        return ["source"] if record.get("hit") else []


class _Gate:
    @staticmethod
    def amount_cap(record):
        return 230_000_000


def test_frozen_v5_positive_rejects_bool_amount_and_construction() -> None:
    assert not frozen_v5_positive({"meta": {"입찰추정가격": True}, "hit": True}, _Hits, _Gate)
    assert not frozen_v5_positive(
        {"meta": {"입찰추정가격": 300_000_000, "업무구분": "공사"}, "hit": True},
        _Hits, _Gate,
    )
    assert frozen_v5_positive({"meta": {"입찰추정가격": 300_000_000}, "hit": True}, _Hits, _Gate)
