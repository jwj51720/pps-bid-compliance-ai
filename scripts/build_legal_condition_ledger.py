#!/usr/bin/env python3
"""Materialize a complete source ledger behind concise legal guardrails.

The ledger deliberately keeps the *entire selected official chunk text* for
each v/profile relation.  A summary may be short for Gemma, but audit must
never depend on a short paraphrase being complete.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_four_profile_group_law_bundles import PROFILES, _keys_for
from scripts.build_four_profile_group_legal_summaries import _summary_for
from scripts.build_routed_law_bundles import _chunks
from src.legal_groups import FOUR_WAY_ITEM_GROUPS, validate_groups


OUTPUT = ROOT / "data/derived/legal_condition_ledger_v1.json"


def _source_row(chunk: object) -> dict[str, str]:
    return {
        "key": chunk.key,
        "title": chunk.title,
        "source": chunk.source,
        "selector": chunk.selector,
        "source_sha256": hashlib.sha256(
            (ROOT / "data/raw/open/data/법령패키지/법령" / chunk.source).read_bytes()
        ).hexdigest(),
        "chunk_sha256": hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
        # This is the anti-omission record.  It is audit data, not a model prompt.
        "official_text": chunk.text,
    }


def main() -> int:
    validate_groups(FOUR_WAY_ITEM_GROUPS)
    chunks = _chunks()
    entries: dict[str, object] = {}
    for profile, profile_spec in PROFILES.items():
        direction = profile_spec["direction"]
        for group in FOUR_WAY_ITEM_GROUPS:
            per_item, _ = _keys_for(profile, group.items)
            item_rows = []
            for item in group.items:
                keys = per_item[item]
                inactive_reason = profile_spec["inactive_items"].get(item)
                if item == "v24":
                    if keys:
                        raise ValueError("v24 must not own a law chunk")
                elif not keys and not inactive_reason:
                    raise ValueError(f"uncovered active item: {profile}/{item}")
                item_rows.append(
                    {
                        "item": item,
                        "model_summary": _summary_for(direction, item),
                        "source_chunk_keys": keys,
                        "inactive_reason": inactive_reason,
                        "official_sources": [_source_row(chunks[key]) for key in keys],
                    }
                )
            entries[f"{profile}/{group.group_id}"] = {
                "profile": profile,
                "group": group.group_id,
                "items": item_rows,
            }
    payload = {
        "schema_version": 1,
        "purpose": "anti-omission legal condition ledger; concise model summaries are reviewed against retained complete organizer source chunks",
        "source_root": "data/raw/open/data/법령패키지/법령",
        "profiles": list(PROFILES),
        "groups": [group.group_id for group in FOUR_WAY_ITEM_GROUPS],
        "entries": entries,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)
    print(f"wrote {len(entries)} profile/group ledger entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
