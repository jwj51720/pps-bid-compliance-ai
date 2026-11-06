from src.precedent_audit import bm25_term_score, profile_compatibility, tokenize


def test_tokenize_normalizes_and_preserves_korean_and_numbers():
    assert tokenize("소기업·소상공인 1,200만원") == ["소기업·소상공인", "200만원"]


def test_bm25_term_score_rewards_rare_observed_term():
    rare = bm25_term_score(1, 1, 100, 100, 100)
    common = bm25_term_score(1, 90, 100, 100, 100)
    assert rare > common > 0


def test_profile_compatibility_ignores_missing_and_compares_present_fields():
    result = profile_compatibility(
        {"법": "지방", "방법": "제한", "유형": None},
        {"법": "지방", "방법": "수의", "유형": "물품"},
        ("법", "방법", "유형"),
    )
    assert result == {
        "compared_fields": ["법", "방법"],
        "matched_fields": ["법"],
        "rate": 0.5,
    }
