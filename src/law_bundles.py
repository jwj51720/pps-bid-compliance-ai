"""Deterministic selection of fixed official-law bundles from organizer metadata."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROUTING_VERSION = "metadata_v1"


def _display_label(title: str, selector: object) -> str:
    if not isinstance(selector, str):
        return title
    if selector.startswith("article_"):
        number = selector.removeprefix("article_").replace("조의", "조의")
        return f"{title} 제{number}조" if "조의" not in number else f"{title} 제{number}"
    return title


@dataclass(frozen=True)
class LawBundleRoute:
    profile: str
    reference_text: str
    reference_path: Path
    reference_sha256: str
    chunk_labels: dict[str, str]


class MetadataLawBundleRouter:
    """Route only on organizer metadata; never infer a law profile from prose."""

    def __init__(self, bundle_dir: str | Path) -> None:
        self.bundle_dir = Path(bundle_dir)
        manifest = json.loads((self.bundle_dir / "manifest.json").read_text(encoding="utf-8"))
        bundles = manifest.get("bundles")
        if not isinstance(bundles, dict):
            raise ValueError("law bundle manifest must contain bundles")
        self._bundles: dict[str, LawBundleRoute] = {}
        for profile, entry in bundles.items():
            relative_path, expected_sha = entry.get("path"), entry.get("sha256")
            if not isinstance(relative_path, str) or not isinstance(expected_sha, str):
                raise ValueError(f"law bundle manifest entry is invalid: {profile}")
            path = self.bundle_dir / Path(relative_path).name
            text = path.read_text(encoding="utf-8")
            actual_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if actual_sha != expected_sha:
                raise ValueError(f"law bundle hash mismatch: {profile}")
            chunks = entry.get("chunks")
            if not isinstance(chunks, list):
                raise ValueError(f"law bundle manifest chunks are missing: {profile}")
            chunk_labels = {
                value["key"]: _display_label(value["title"], value.get("selector"))
                for value in chunks
                if isinstance(value, dict)
                and isinstance(value.get("key"), str)
                and isinstance(value.get("title"), str)
            }
            self._bundles[profile] = LawBundleRoute(
                profile, text, path, actual_sha, chunk_labels
            )

    @staticmethod
    def profile_for_record(record: dict[str, Any]) -> str:
        meta = record.get("meta") or {}
        law, method, award = meta.get("적용계약법"), meta.get("계약방법"), meta.get("낙찰방법")
        if law == "국가계약법":
            return "national_complete"
        if law != "지방계약법":
            raise ValueError(f"cannot route {record.get('id')}: unsupported 적용계약법={law!r}")
        small = method == "수의계약" or award == "소액수의견적"
        negotiated = award == "협상에의한계약"
        if small and negotiated:
            return "local_small_negotiated_complete"
        if small:
            return "local_small_complete"
        if negotiated:
            return "local_negotiated_complete"
        return "local_general_complete"

    def route(self, record: dict[str, Any]) -> LawBundleRoute:
        profile = self.profile_for_record(record)
        if profile not in self._bundles:
            raise ValueError(f"law bundle is missing profile: {profile}")
        return self._bundles[profile]

    def audit_row(self, record: dict[str, Any]) -> dict[str, Any]:
        route = self.route(record)
        meta = record.get("meta") or {}
        return {
            "id": record["id"], "routing_version": ROUTING_VERSION,
            "profile": route.profile, "reference_path": str(route.reference_path),
            "reference_sha256": route.reference_sha256,
            "metadata": {key: meta.get(key) for key in ("적용계약법", "계약방법", "낙찰방법")},
        }

    def navigation_text(self, record: dict[str, Any]) -> str:
        """Return the item-to-source navigation instruction shown to the LLM."""
        route = self.route(record)
        meta = record.get("meta") or {}
        contract_law = meta.get("적용계약법")
        references = _ITEM_REFERENCE_KEYS["national" if contract_law == "국가계약법" else "local"]
        lines = [
            "[항목별 공식 참고자료 안내]",
            f"이 공고에는 `{route.profile}` 법령 묶음이 선택되었습니다.",
            "각 v는 아래에 적힌 출처 조각만 먼저 읽어 적용기준을 확인하십시오. 다른 항목의 조문을 섞어 적용하지 마십시오.",
            "법령은 적용기준일 뿐 위반 근거문구가 아닙니다. 1 판정과 근거문구는 언제나 대상 공고 문서에서 확인해야 합니다.",
        ]
        for item, keys in references.items():
            titles = [route.chunk_labels[key] for key in keys if key in route.chunk_labels]
            if titles:
                lines.append(f"- {item}: " + " / ".join(titles))
            elif item == "v24":
                lines.append("- v24: 법령 참고자료 없음. 공고 문서와 나라장터 metadata를 직접 대조합니다.")
            else:
                lines.append(f"- {item}: 현재 metadata상 이 법령 조각은 적용 대상이 아닙니다. 항목 카드의 적용조건을 따르십시오.")
        return "\n".join(lines)

    def group_bundle(self, record: dict[str, Any], group_id: str) -> LawBundleRoute:
        """Load one audited v-group bundle from the legacy 12-group artifact."""
        profile = self.profile_for_record(record)
        manifest = json.loads((self.bundle_dir / "manifest.json").read_text(encoding="utf-8"))
        entry = (manifest.get("group_bundles") or {}).get(f"{profile}/{group_id}")
        if not isinstance(entry, dict):
            raise ValueError(f"legacy group bundle missing: {profile}/{group_id}")
        relative_path, expected_sha = entry.get("path"), entry.get("sha256")
        if not isinstance(relative_path, str) or not isinstance(expected_sha, str):
            raise ValueError(f"legacy group bundle entry invalid: {profile}/{group_id}")
        path = self.bundle_dir.parent.parent.parent / relative_path
        text = path.read_text(encoding="utf-8")
        actual_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if actual_sha != expected_sha:
            raise ValueError(f"legacy group bundle hash mismatch: {profile}/{group_id}")
        return LawBundleRoute(profile, text, path, actual_sha, {})


class FourProfileGroupLawBundleRouter:
    """Route a fresh 4-profile × 4-v-group official-law bundle set.

    This class intentionally does not reuse the prior complete notice bundles.
    Each lookup verifies the separately generated profile/group text against its
    manifest hash before a final prompt can use it.
    """

    ROUTING_VERSION = "metadata_profile_group_v2"

    def __init__(self, bundle_dir: str | Path) -> None:
        self.bundle_dir = Path(bundle_dir)
        manifest = json.loads((self.bundle_dir / "manifest.json").read_text(encoding="utf-8"))
        entries = manifest.get("profile_group_bundles")
        if manifest.get("routing_version") != self.ROUTING_VERSION or not isinstance(entries, dict):
            raise ValueError("four-profile group bundle manifest is invalid")
        self._entries = entries

    @staticmethod
    def profile_for_record(record: dict[str, Any]) -> str:
        meta = record.get("meta") or {}
        law, method, award = meta.get("적용계약법"), meta.get("계약방법"), meta.get("낙찰방법")
        if law == "국가계약법":
            return "national"
        if law != "지방계약법":
            raise ValueError(f"cannot route {record.get('id')}: unsupported 적용계약법={law!r}")
        small = method == "수의계약" or award == "소액수의견적"
        negotiated = award == "협상에의한계약"
        if small and negotiated:
            raise ValueError(
                f"cannot route {record.get('id')}: local small+negotiated needs an unbuilt fifth profile"
            )
        if small:
            return "local_small"
        if negotiated:
            return "local_negotiated"
        return "local_general"

    def route(self, record: dict[str, Any]) -> LawBundleRoute:
        # The grouped runner uses profile for audit; a specific group bundle is
        # selected through group_bundle below.
        profile = self.profile_for_record(record)
        return LawBundleRoute(profile, "", self.bundle_dir, "", {})

    def group_bundle(self, record: dict[str, Any], group_id: str) -> LawBundleRoute:
        profile = self.profile_for_record(record)
        entry = self._entries.get(f"{profile}/{group_id}")
        if not isinstance(entry, dict):
            raise ValueError(f"four-profile group bundle missing: {profile}/{group_id}")
        relative_path, expected_sha = entry.get("path"), entry.get("sha256")
        if not isinstance(relative_path, str) or not isinstance(expected_sha, str):
            raise ValueError(f"four-profile group bundle entry invalid: {profile}/{group_id}")
        path = self.bundle_dir / relative_path
        text = path.read_text(encoding="utf-8")
        actual_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if actual_sha != expected_sha:
            raise ValueError(f"four-profile group bundle hash mismatch: {profile}/{group_id}")
        labels = {
            value["key"]: _display_label(value["title"], value.get("selector"))
            for value in entry.get("chunks", [])
            if isinstance(value, dict) and isinstance(value.get("key"), str)
            and isinstance(value.get("title"), str)
        }
        return LawBundleRoute(profile, text, path, actual_sha, labels)

    def navigation_text(
        self, record: dict[str, Any], group_id: str, items: tuple[str, ...]
    ) -> str:
        bundle = self.group_bundle(record, group_id)
        entry = self._entries[f"{bundle.profile}/{group_id}"]
        item_keys = entry.get("item_chunk_keys", {})
        lines = [
            "[이 호출의 공식 참고자료 안내]",
            f"이 공고에는 `{bundle.profile}`, 이 v 그룹에는 `{group_id}` 공식 조문 묶음이 선택되었습니다.",
            "각 v는 아래 출처 조각만 적용기준으로 읽으십시오. 법령은 evidence가 아니며, 1의 근거문구는 대상 공고문서에서만 복사합니다.",
        ]
        for item in items:
            keys = item_keys.get(item, []) if isinstance(item_keys, dict) else []
            titles = [bundle.chunk_labels[key] for key in keys if key in bundle.chunk_labels]
            if titles:
                lines.append(f"- {item}: " + " / ".join(titles))
            else:
                lines.append(f"- {item}: 이 공고 profile에서 법령 적용대상이 아니거나 조문 참고자료가 없습니다. 항목 카드와 metadata를 따르십시오.")
        return "\n".join(lines)


_ITEM_REFERENCE_KEYS = {
    "national": {
        "v1": ("national_decree_12", "national_decree_21"), "v2": ("national_decree_21", "national_rule_25"),
        "v3": ("national_decree_21", "national_rule_25", "government_guide_chapter_2"), "v4": ("government_guide_chapter_2",),
        "v5": ("national_decree_21", "price_notice"), "v6": ("national_rule_25",), "v7": ("national_rule_25",), "v8": ("national_rule_25",),
        "v9": ("government_guide_chapter_2",), "v10": ("sme_law_9",), "v11": ("national_decree_21", "sme_law_7"),
        "v12": ("national_decree_21",), "v13": ("national_decree_21", "sme_law_7"),
        "v14": ("national_decree_21", "sme_decree_2조의2", "sme_decree_2조의3"), "v15": ("national_decree_21", "sme_decree_2조의2", "sme_decree_2조의3"),
        "v16": ("national_decree_21", "sme_decree_2조의2", "sme_decree_2조의3"), "v17": ("national_decree_21", "sme_decree_2조의2", "sme_decree_2조의3"),
        "v18": ("national_decree_21", "sme_decree_2조의2", "sme_decree_2조의3"), "v19": ("national_decree_12", "national_rule_17", "government_guide_chapter_2"),
        "v20": ("sw_law_48", "sw_guideline_articles_2_3", "sw_guideline_appendix_1"), "v21": ("national_joint_article_9",),
        "v22": ("national_decree_43",), "v23": (), "v24": (),
    },
    "local": {
        "v1": ("local_decree_13", "local_decree_20"), "v2": ("local_decree_20", "local_rule_25", "local_guide_c1_item_7"),
        "v3": ("local_decree_20", "local_rule_25"), "v4": ("local_guide_c1_item_7",), "v5": ("local_decree_20", "local_rule_24", "price_notice"),
        "v6": ("local_rule_25", "local_guide_small_contract"), "v7": ("local_rule_25", "local_guide_small_contract"), "v8": ("local_rule_25", "local_guide_small_contract"),
        "v9": ("local_guide_c1_item_7",), "v10": ("sme_law_9",), "v11": ("local_decree_20", "sme_law_7"),
        "v12": ("local_decree_20",), "v13": ("local_decree_20", "sme_law_7"),
        "v14": ("local_decree_20", "sme_decree_2조의2", "sme_decree_2조의3"), "v15": ("local_decree_20", "sme_decree_2조의2", "sme_decree_2조의3"),
        "v16": ("local_decree_20", "sme_decree_2조의2", "sme_decree_2조의3"), "v17": ("local_decree_20", "sme_decree_2조의2", "sme_decree_2조의3"),
        "v18": ("local_decree_20", "sme_decree_2조의2", "sme_decree_2조의3"), "v19": ("local_decree_13", "local_rule_17", "local_guide_c1_item_7"),
        "v20": ("sw_law_48", "sw_guideline_articles_2_3", "sw_guideline_appendix_1"), "v21": ("local_guide_joint",),
        "v22": ("local_decree_43",), "v23": ("local_decree_35", "local_award_ch7_s3"), "v24": (),
    },
}
