#!/usr/bin/env python3
"""Build a fresh 4-profile × 4-v-group law bundle set from organizer sources.

The generated texts are read directly from the organizer law package on every
build. They do not read, concatenate, or copy the earlier complete-profile
bundles. The manifest records the item-to-chunk mapping for all sixteen bundles
and the metadata-only routing contract.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_routed_law_bundles import ITEM_KEYS, _chunks
from src.legal_groups import FOUR_WAY_ITEM_GROUPS, validate_groups


OUTPUT_DIR = ROOT / "data/derived/legal_reference_profile_group_v3"
ROUTING_VERSION = "metadata_profile_group_v2"

PROFILES = {
    "national": {
        "direction": "national",
        "metadata_rule": {"적용계약법": "국가계약법"},
        "optional_keys": set(),
        "inactive_items": {"v23": "국가계약 건에서는 항목표상 위반 성립 불가"},
    },
    "local_general": {
        "direction": "local",
        "metadata_rule": {"적용계약법": "지방계약법", "not": "수의계약·소액수의견적·협상에의한계약"},
        "optional_keys": set(),
        "inactive_items": {"v23": "지방 협상계약이 아니므로 항목 적용대상 아님"},
    },
    "local_small": {
        "direction": "local",
        "metadata_rule": {"적용계약법": "지방계약법", "계약방법_or_낙찰방법": "수의계약 또는 소액수의견적"},
        "optional_keys": {"local_guide_small_contract"},
        "inactive_items": {"v23": "지방 협상계약이 아니므로 항목 적용대상 아님"},
    },
    "local_negotiated": {
        "direction": "local",
        "metadata_rule": {"적용계약법": "지방계약법", "낙찰방법": "협상에의한계약"},
        "optional_keys": {"local_award_ch7_s3", "local_decree_35"},
        "inactive_items": {},
    },
}


def _render_for_model(chunk: object) -> str:
    """Keep only the human legal-document heading and exact source text.

    Source file paths, selectors, keys, profiles, and routing mechanics remain
    in the manifest for audit; they are not legal content for the LLM to read.
    """
    return f"## {chunk.title}\n{chunk.text}"


def _ordered_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _keys_for(profile: str, items: tuple[str, ...]) -> tuple[dict[str, list[str]], list[str]]:
    spec = PROFILES[profile]
    direction = spec["direction"]
    inactive = spec["inactive_items"]
    item_keys: dict[str, list[str]] = {}
    selected: list[str] = []
    for item in items:
        if item in inactive:
            item_keys[item] = []
            continue
        keys = list(ITEM_KEYS[direction][item])
        # The small-contract and negotiated overlays are profile-specific facts,
        # not prose guesses. Keep them only when the routing metadata proves the
        # corresponding profile.
        if profile != "local_small":
            keys = [key for key in keys if key != "local_guide_small_contract"]
        if profile != "local_negotiated":
            keys = [key for key in keys if key not in {"local_award_ch7_s3", "local_decree_35"}]
        item_keys[item] = keys
        selected.extend(keys)
    return item_keys, _ordered_unique(selected)


def main() -> int:
    validate_groups(FOUR_WAY_ITEM_GROUPS)
    chunks = _chunks()  # Fresh extraction from data/raw/open/data/법령패키지/법령.
    groups_dir = OUTPUT_DIR / "groups"
    groups_dir.mkdir(parents=True, exist_ok=True)
    profile_group_bundles: dict[str, object] = {}
    profile_group_map: dict[str, object] = {}

    for profile, profile_spec in PROFILES.items():
        for group in FOUR_WAY_ITEM_GROUPS:
            per_item, keys = _keys_for(profile, group.items)
            selected = [chunks[key] for key in keys]
            text = "\n\n".join(_render_for_model(chunk) for chunk in selected)
            if text:
                text += "\n"
            relative_path = Path("groups") / f"{profile}__{group.group_id}.txt"
            path = OUTPUT_DIR / relative_path
            path.write_text(text, encoding="utf-8")
            sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
            chunk_rows = [
                {
                    "key": chunk.key,
                    "title": chunk.title,
                    "source": chunk.source,
                    "selector": chunk.selector,
                    "source_sha256": hashlib.sha256(
                        (ROOT / "data/raw/open/data/법령패키지/법령" / chunk.source).read_bytes()
                    ).hexdigest(),
                    "chunk_sha256": hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
                }
                for chunk in selected
            ]
            key = f"{profile}/{group.group_id}"
            entry = {
                "path": str(relative_path),
                "items": list(group.items),
                "item_chunk_keys": per_item,
                "chunk_keys": keys,
                "chunks": chunk_rows,
                "sha256": sha,
                "characters": len(text),
                "inactive_items": {
                    item: profile_spec["inactive_items"][item]
                    for item in group.items if item in profile_spec["inactive_items"]
                },
            }
            profile_group_bundles[key] = entry
            profile_group_map[key] = {
                "profile": profile,
                "profile_metadata_rule": profile_spec["metadata_rule"],
                "group": group.group_id,
                "items": list(group.items),
                "item_chunk_keys": per_item,
                "inactive_items": entry["inactive_items"],
                "competition_product_context": {
                    "v10_to_v18": "existing exact organizer CSV index; not copied into law text",
                },
            }

    manifest = {
        "schema_version": 3,
        "routing_version": ROUTING_VERSION,
        "purpose": "fresh official-law fixed context for four metadata profiles by four v groups; model text contains only legal document headings and exact text",
        "source_root": "data/raw/open/data/법령패키지/법령",
        "profile_count": 4,
        "group_count": 4,
        "bundle_count": len(profile_group_bundles),
        "routing_contract": {
            "metadata_fields": ["적용계약법", "계약방법", "낙찰방법"],
            "unsupported_combination": "지방계약법 + small-contract + negotiated; fail closed until a separately audited fifth profile is built",
        },
        "profile_group_bundles": profile_group_bundles,
        "profile_group_map": profile_group_map,
    }
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUTPUT_DIR / "mapping.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "mapping_field": "profile_group_map",
                "source_manifest": "manifest.json",
                "profile_group_map": profile_group_map,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT_DIR / "manifest.json")
    print(f"built {len(profile_group_bundles)} fresh profile/group bundles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
