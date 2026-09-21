import json

from scripts.build_precedent_pool_s0b import build_pool


def test_build_pool_uses_only_card_terms_and_unlabeled_docs(tmp_path):
    cards = {"cards": {f"v{i}": {"prompt_text": "특정 제조사 모델 제한"} for i in range(1, 25)}}
    cards_path = tmp_path / "cards.json"
    cards_path.write_text(json.dumps(cards, ensure_ascii=False), encoding="utf-8")
    import gzip

    train_path = tmp_path / "train.jsonl.gz"
    row = {"id": "PPS-D-1", "meta": {}, "docs": [
        {"doc_id": "D0", "type": "공고문", "text": "특정 제조사 모델 제한"}
    ]}
    with gzip.open(train_path, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    report = build_pool(train_path, cards_path, 1)
    assert report["unique_notice_ids"] == ["PPS-D-1"]
    assert report["items"]["v9"][0]["notice_id"] == "PPS-D-1"
