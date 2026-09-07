from src.fact_precedent_audit import rank_auc, source_fragments


def test_source_fragments_cover_long_paragraph_with_overlap():
    text = "a" * 1_050
    fragments = source_fragments(text, max_chars=500, overlap_chars=100)
    assert len(fragments) == 3
    assert fragments[0][-100:] == fragments[1][:100]
    assert fragments[-1].endswith("a" * 250)


def test_source_fragments_keeps_short_paragraphs_together():
    assert source_fragments("첫 문단\n\n둘째 문단", max_chars=100, overlap_chars=20) == ["첫 문단\n\n둘째 문단"]


def test_rank_auc_handles_wins_ties_and_empty_groups():
    assert rank_auc([0.9, 0.5], [0.1, 0.5]) == 0.875
    assert rank_auc([], [0.1]) is None
