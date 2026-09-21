#!/usr/bin/env python3
"""Build readable but condition-complete 4-profile x 4-group law bundles.

The model text retains every substantive character of each selected organizer
law chunk.  Only amendment-history tags, XML wrappers, and table border glyphs
are normalized.  A short v-level reading guide precedes the normalized source;
it never substitutes for the retained source text.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_four_profile_group_law_bundles import PROFILES, _keys_for
from scripts.build_four_profile_group_legal_summaries import _summary_for
from scripts.build_routed_law_bundles import _chunks
from src.legal_groups import FOUR_WAY_ITEM_GROUPS, validate_groups


OUTPUT_DIR = ROOT / "data/derived/legal_complete_profile_group_v1"
ROUTING_VERSION = "metadata_profile_group_v2"


def normalize_official_text(text: str) -> str:
    """Remove presentation-only artifacts without removing legal body text."""
    value = text.replace("<![CDATA[", "").replace("]]>", "")
    # The package marks amendment history in angle brackets.  The legal body
    # and every numbered paragraph/item remain unchanged.
    value = re.sub(r"\s*<(?:개정|신설|단서신설|전문개정|본조신설|제[0-9]+항에서 이동)[^>]*>", "", value)
    value = re.sub(r"\s*\[(?:전문개정|본조신설)[^\]]*\]", "", value)
    value = value.translate(str.maketrans({
        "┏": "", "┓": "", "┗": "", "┛": "", "┠": "", "┨": "", "━": "", "┃": "", "│": " | ", "┯": " | ", "┷": " | ",
    }))
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def main() -> int:
    validate_groups(FOUR_WAY_ITEM_GROUPS)
    chunks = _chunks()
    groups_dir = OUTPUT_DIR / "groups"
    groups_dir.mkdir(parents=True, exist_ok=True)
    entries: dict[str, object] = {}
    for profile, profile_spec in PROFILES.items():
        direction = profile_spec["direction"]
        for group in FOUR_WAY_ITEM_GROUPS:
            per_item, keys = _keys_for(profile, group.items)
            guide = "\n".join(f"- {item}: {_summary_for(direction, item)}" for item in group.items)
            rendered_chunks = []
            chunk_rows = []
            for key in keys:
                chunk = chunks[key]
                normalized = normalize_official_text(chunk.text)
                rendered_chunks.append(f"## {chunk.title}\n{normalized}")
                chunk_rows.append({
                    "key": key, "title": chunk.title, "source": chunk.source,
                    "selector": chunk.selector,
                    "source_sha256": hashlib.sha256(
                        (ROOT / "data/raw/open/data/법령패키지/법령" / chunk.source).read_bytes()
                    ).hexdigest(),
                    "chunk_sha256": hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
                    "normalized_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
                    "original_characters": len(chunk.text),
                    "normalized_characters": len(normalized),
                })
            text = (
                "# 판정 길잡이\n"
                "아래 항목별 안내로 확인 순서를 잡은 뒤, 이어지는 법령 본문에서 적용 전제·예외·수치·기간을 모두 확인한다.\n"
                + guide
                + "\n\n# 법령 본문\n"
                + "\n\n".join(rendered_chunks)
                + "\n"
            )
            relative = Path("groups") / f"{profile}__{group.group_id}.txt"
            path = OUTPUT_DIR / relative
            path.write_text(text, encoding="utf-8")
            name = f"{profile}/{group.group_id}"
            entries[name] = {
                "path": str(relative), "items": list(group.items),
                "item_chunk_keys": per_item, "chunk_keys": keys, "chunks": chunk_rows,
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "characters": len(text),
            }
    manifest = {
        "schema_version": 1, "routing_version": ROUTING_VERSION,
        "purpose": "condition-complete organizer-law context with presentation-only normalization and a non-authoritative reading guide",
        "source_root": "data/raw/open/data/법령패키지/법령",
        "normalization_contract": "only amendment-history tags, XML wrappers, table-border glyphs, and whitespace are removed; legal body text is retained",
        "profile_count": 4, "group_count": 4, "bundle_count": len(entries),
        "profile_group_bundles": entries,
    }
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT_DIR / "manifest.json")
    print(f"built {len(entries)} condition-complete normalized law bundles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
