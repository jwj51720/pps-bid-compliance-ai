#!/usr/bin/env python3
"""S0B: create a label-blind, item-conditioned unlabeled pool manifest.

The manifest is intentionally based only on fixed decision-card text and the
unlabeled source corpus.  It is an inspectable candidate pool, not a label,
retrieval policy, or final-prompt asset.
"""

from __future__ import annotations

import argparse
import gzip
import heapq
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.precedent_audit import bm25_term_score, tokenize


ITEMS = tuple(f"v{number}" for number in range(1, 25))


def records(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def build_pool(train_path: Path, cards_path: Path, top_per_item: int) -> dict[str, Any]:
    cards = json.loads(cards_path.read_text(encoding="utf-8"))["cards"]
    queries = {item: tuple(sorted(set(tokenize(cards[item]["prompt_text"])))) for item in ITEMS}
    query_by_term: dict[str, list[str]] = defaultdict(list)
    for item, terms in queries.items():
        for term in terms:
            query_by_term[term].append(item)
    relevant_terms = set(query_by_term)
    df: Counter[str] = Counter()
    document_count = 0
    token_count = 0
    document_types: Counter[str] = Counter()
    for record in records(train_path):
        for document in record["docs"]:
            tokens = tokenize(document["text"])
            document_count += 1
            token_count += len(tokens)
            document_types[document["type"]] += 1
            df.update(set(tokens) & relevant_terms)
    average_length = token_count / max(document_count, 1)
    heaps: dict[str, list[tuple[float, str, str, dict[str, Any]]]] = {
        item: [] for item in ITEMS
    }
    for record in records(train_path):
        for document in record["docs"]:
            tokens = tokenize(document["text"])
            counts = Counter(tokens)
            scores: defaultdict[str, float] = defaultdict(float)
            matches: defaultdict[str, list[str]] = defaultdict(list)
            for term in set(counts) & relevant_terms:
                score = bm25_term_score(
                    counts[term], df[term], document_count, len(tokens), average_length
                )
                for item in query_by_term[term]:
                    scores[item] += score
                    matches[item].append(term)
            for item, score in scores.items():
                matched = sorted(matches[item])
                first = min(
                    (document["text"].lower().find(term) for term in matched
                     if document["text"].lower().find(term) >= 0), default=0
                )
                snippet = document["text"][max(0, first - 100):first + 360]
                candidate = {
                    "item": item,
                    "notice_id": record["id"],
                    "doc_id": document["doc_id"],
                    "document_type": document["type"],
                    "score": round(score, 6),
                    "matched_card_terms": matched,
                    "metadata": record["meta"],
                    "snippet": snippet,
                }
                entry = (score, record["id"], document["doc_id"], candidate)
                heap = heaps[item]
                if len(heap) < top_per_item:
                    heapq.heappush(heap, entry)
                elif entry[:3] > heap[0][:3]:
                    heapq.heapreplace(heap, entry)
    per_item = {
        item: [entry[3] for entry in sorted(heap, reverse=True)]
        for item, heap in heaps.items()
    }
    unique_notices = sorted({row["notice_id"] for rows in per_item.values() for row in rows})
    return {
        "audit": "precedent_s0b_card_pool",
        "scope": {
            "train_path": str(train_path),
            "decision_cards_path": str(cards_path),
            "top_per_item": top_per_item,
            "warning": (
                "Pool selection is label-blind and uses only fixed cards plus unlabeled source. "
                "It is not a self-label, a final retrieval policy, or a submission asset."
            ),
        },
        "corpus": {"document_count": document_count, "document_types": dict(document_types)},
        "items": per_item,
        "unique_notice_ids": unique_notices,
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# S0B — card-conditioned unlabeled candidate pool",
        "",
        "이 manifest는 fixed card와 train 원문만으로 만든 label-blind 후보군이다. "
        "각 후보를 사람이 먼저 검사해 semantic boilerplate가 주된 결과인지 확인한 뒤에만 "
        "self-label call을 고려한다.",
        "",
        f"- items: {len(report['items'])}",
        f"- top candidates/item: {report['scope']['top_per_item']}",
        f"- unique notices: {len(report['unique_notice_ids'])}",
        "",
        "| item | top candidate document type | matched terms |",
        "|---|---|---|",
    ]
    for item, candidates in report["items"].items():
        top = candidates[0] if candidates else {}
        lines.append(
            f"| {item} | {top.get('document_type', '-')} | "
            f"{', '.join(top.get('matched_card_terms', [])[:8])} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", default="data/raw/open/train_unlabeled.jsonl.gz")
    parser.add_argument("--cards", default="data/derived/decision_cards_v6.json")
    parser.add_argument("--top-per-item", type=int, default=20)
    parser.add_argument("--output-dir", default="outputs/precedent-s0b-card-pool")
    args = parser.parse_args()
    if args.top_per_item <= 0:
        raise ValueError("--top-per-item must be positive")
    report = build_pool(Path(args.train), Path(args.cards), args.top_per_item)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "pool.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "pool.md").write_text(markdown(report), encoding="utf-8")
    (output_dir / "notice_ids.json").write_text(
        json.dumps(report["unique_notice_ids"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output_dir / "pool.md")
    print(f"unique notices: {len(report['unique_notice_ids'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
