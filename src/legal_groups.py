"""Fixed v-item execution groups derived from the audited legal-reference map.

These groups are a retrieval/execution specification, not a semantic rule engine:
they only state which requested output keys share the same official references.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LegalItemGroup:
    group_id: str
    items: tuple[str, ...]


LEGAL_ITEM_GROUPS = (
    LegalItemGroup("G01_qualification", ("v1", "v19")),
    LegalItemGroup("G02_performance", ("v2", "v3")),
    LegalItemGroup("G03_specific_requirement", ("v4", "v9")),
    LegalItemGroup("G04_regional_small_contract", ("v6", "v7", "v8")),
    LegalItemGroup("G05_threshold_region", ("v5",)),
    LegalItemGroup("G06_competition_product", ("v10", "v11", "v12", "v13")),
    LegalItemGroup("G07_general_product", ("v14", "v15", "v16", "v17", "v18")),
    LegalItemGroup("G08_software", ("v20",)),
    LegalItemGroup("G09_joint_contract", ("v21",)),
    LegalItemGroup("G10_site_briefing_qualification", ("v22",)),
    LegalItemGroup("G11_site_briefing_period", ("v23",)),
    LegalItemGroup("G12_notice_metadata_consistency", ("v24",)),
)


FOUR_WAY_ITEM_GROUPS = (
    LegalItemGroup("G01_qualification_threshold", ("v1", "v2", "v3", "v4", "v5")),
    LegalItemGroup("G02_document_restrictions", ("v6", "v7", "v8", "v9", "v19")),
    LegalItemGroup("G03_product_restrictions", ("v10", "v11", "v12", "v13", "v14", "v15", "v16", "v17", "v18")),
    LegalItemGroup("G04_procedure_and_consistency", ("v20", "v21", "v22", "v23", "v24")),
)

THREE_WAY_ITEM_GROUPS = (
    LegalItemGroup(
        "G01_participation_and_document_restrictions",
        ("v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v19"),
    ),
    LegalItemGroup(
        "G02_product_and_sme_restrictions",
        ("v10", "v11", "v12", "v13", "v14", "v15", "v16", "v17", "v18"),
    ),
    LegalItemGroup(
        "G03_special_procedure_and_consistency",
        ("v20", "v21", "v22", "v23", "v24"),
    ),
)


def groups_for_scheme(scheme: str) -> tuple[LegalItemGroup, ...]:
    """Return a fixed, auditable item partition for a grouped-call ablation."""
    groups_by_scheme = {
        "law_overlap_12": LEGAL_ITEM_GROUPS,
        "four_way": FOUR_WAY_ITEM_GROUPS,
        "three_way": THREE_WAY_ITEM_GROUPS,
    }
    try:
        groups = groups_by_scheme[scheme]
    except KeyError as exc:
        raise ValueError(f"unknown item grouping scheme: {scheme}") from exc
    validate_groups(groups)
    return groups


def validate_groups(groups: tuple[LegalItemGroup, ...] = LEGAL_ITEM_GROUPS) -> None:
    expected = {f"v{index}" for index in range(1, 25)}
    actual = {item for group in groups for item in group.items}
    if actual != expected or sum(len(group.items) for group in groups) != 24:
        raise ValueError("legal item groups must partition v1..v24 exactly once")
