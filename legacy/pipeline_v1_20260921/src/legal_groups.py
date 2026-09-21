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

# EXP133's narrow follow-up to the four-way observation. G02 is the only group
# whose replacement improved the exact 24-item baseline on the frozen fast
# panel, independent holdout, and dev-200 counterfactual audit. This remains an
# execution partition, never a Python label rule or an overlapping overlay.
DOCUMENT_RESTRICTIONS_TWO_WAY_GROUPS = (
    LegalItemGroup(
        "G01_remainder_items",
        (
            "v1", "v2", "v3", "v4", "v5", "v10", "v11", "v12", "v13",
            "v14", "v15", "v16", "v17", "v18", "v20", "v21", "v22", "v23", "v24",
        ),
    ),
    LegalItemGroup("G02_document_restrictions", ("v6", "v7", "v8", "v9", "v19")),
)

# Complete-source 32k probe: two disjoint final jobs divided by truth-condition
# family, not by dev labels or a post-hoc error list. The first job reads
# qualification/document/procedure/metadata consistency conditions; the second
# reads the mutually related exact-product and whole-notice absence conditions.
COMPLETE_FACT_BALANCED_TWO_WAY_GROUPS = (
    LegalItemGroup(
        "G01_qualification_document_procedure_consistency",
        ("v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v19", "v21", "v22", "v23", "v24"),
    ),
    LegalItemGroup(
        "G02_product_and_absence",
        ("v10", "v11", "v12", "v13", "v14", "v15", "v16", "v17", "v18", "v20"),
    ),
)

# This is deliberately not a general overlapping-group mechanism.  EXP139
# preserves the original 24-item call, then makes one focused call for the
# only five-item scope that improved on three cohorts in the prior audit.  The
# runner applies groups in this declared order, so the second response is the
# sole source of these five values.  All other values remain from the exact
# full-call response.  This is an execution/output-scope ablation, never a
# Python label correction.
DOCUMENT_RESTRICTIONS_OVERLAY_GROUPS = (
    LegalItemGroup(
        "G01_full_baseline",
        tuple(f"v{index}" for index in range(1, 25)),
    ),
    LegalItemGroup("G02_document_restrictions_override", ("v6", "v7", "v8", "v9", "v19")),
)

# A bounded three-call draft: retain the organizer full call, then replace two
# disjoint specialist scopes. It deliberately duplicates notice context but
# never combines item grouping with document splitting.
SEMANTIC_VERIFIER_OVERLAY_GROUPS = (
    LegalItemGroup("G01_full_baseline", tuple(f"v{index}" for index in range(1, 25))),
    LegalItemGroup(
        "G02_qualification_document_procedure",
        ("v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v19", "v21", "v22", "v23", "v24"),
    ),
    LegalItemGroup(
        "G03_product_absence",
        ("v10", "v11", "v12", "v13", "v14", "v15", "v16", "v17", "v18", "v20"),
    ),
)

# A source-coverage ablation, not a label rule: v9 is the sole item whose
# organizer definition targets specification/task text. It gets its own group
# so only that item can use complete source-document passes.
DOCUMENT_RESTRICTIONS_V9_SOURCE_GROUPS = (
    LegalItemGroup(
        "G01_remainder_items",
        (
            "v1", "v2", "v3", "v4", "v5", "v10", "v11", "v12", "v13",
            "v14", "v15", "v16", "v17", "v18", "v20", "v21", "v22", "v23", "v24",
        ),
    ),
    LegalItemGroup("G02_document_restrictions", ("v6", "v7", "v8", "v19")),
    LegalItemGroup("G03_specification_model", ("v9",)),
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

# A deliberately small execution ablation: absence detection has the opposite
# truth condition from the other items, so it receives its own model call.
# This is not a legal-reference grouping and does not alter any final labels.
ABSENCE_PRESENCE_ITEM_GROUPS = (
    LegalItemGroup(
        "G01_presence_items",
        ("v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v12", "v13", "v14", "v15", "v17", "v19", "v21", "v22", "v23", "v24"),
    ),
    LegalItemGroup("G02_absence_items", ("v10", "v11", "v16", "v18", "v20")),
)

# v24 is a document-to-metadata consistency task, rather than either a
# document-presence or an absence-detection task. This three-way variant tests
# the cost of giving that comparison task a dedicated response.
ABSENCE_PRESENCE_CONSISTENCY_ITEM_GROUPS = (
    LegalItemGroup(
        "G01_presence_items",
        ("v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v12", "v13", "v14", "v15", "v17", "v19", "v21", "v22", "v23"),
    ),
    LegalItemGroup("G02_absence_items", ("v10", "v11", "v16", "v18", "v20")),
    LegalItemGroup("G03_document_metadata_consistency", ("v24",)),
)


def groups_for_scheme(scheme: str) -> tuple[LegalItemGroup, ...]:
    """Return a fixed, auditable item partition for a grouped-call ablation."""
    groups_by_scheme = {
        "law_overlap_12": LEGAL_ITEM_GROUPS,
        "four_way": FOUR_WAY_ITEM_GROUPS,
        "document_restrictions_two_way_v1": DOCUMENT_RESTRICTIONS_TWO_WAY_GROUPS,
        "complete_fact_balanced_two_way_v1": COMPLETE_FACT_BALANCED_TWO_WAY_GROUPS,
        "document_restrictions_overlay_v1": DOCUMENT_RESTRICTIONS_OVERLAY_GROUPS,
        "semantic_verifier_overlay_v1": SEMANTIC_VERIFIER_OVERLAY_GROUPS,
        "document_restrictions_v9_source_v1": DOCUMENT_RESTRICTIONS_V9_SOURCE_GROUPS,
        "three_way": THREE_WAY_ITEM_GROUPS,
        "absence_presence_v1": ABSENCE_PRESENCE_ITEM_GROUPS,
        "absence_presence_consistency_v1": ABSENCE_PRESENCE_CONSISTENCY_ITEM_GROUPS,
    }
    try:
        groups = groups_by_scheme[scheme]
    except KeyError as exc:
        raise ValueError(f"unknown item grouping scheme: {scheme}") from exc
    if scheme == "document_restrictions_overlay_v1":
        validate_document_restrictions_overlay(groups)
    elif scheme == "semantic_verifier_overlay_v1":
        validate_semantic_verifier_overlay(groups)
    else:
        validate_groups(groups)
    return groups


def validate_groups(groups: tuple[LegalItemGroup, ...] = LEGAL_ITEM_GROUPS) -> None:
    expected = {f"v{index}" for index in range(1, 25)}
    actual = {item for group in groups for item in group.items}
    if actual != expected or sum(len(group.items) for group in groups) != 24:
        raise ValueError("legal item groups must partition v1..v24 exactly once")


def validate_document_restrictions_overlay(
    groups: tuple[LegalItemGroup, ...] = DOCUMENT_RESTRICTIONS_OVERLAY_GROUPS,
) -> None:
    """Validate the one audited overlap used by the two-call overlay probe."""
    if len(groups) != 2:
        raise ValueError("document-restrictions overlay requires exactly two groups")
    expected = tuple(f"v{index}" for index in range(1, 25))
    if groups[0].items != expected:
        raise ValueError("overlay first group must be the ordered full v1..v24 call")
    if groups[1].items != ("v6", "v7", "v8", "v9", "v19"):
        raise ValueError("overlay second group must contain only audited document restrictions")


def validate_semantic_verifier_overlay(
    groups: tuple[LegalItemGroup, ...] = SEMANTIC_VERIFIER_OVERLAY_GROUPS,
) -> None:
    """Validate the sole full-call plus two disjoint-specialist draft."""
    expected = tuple(f"v{index}" for index in range(1, 25))
    if len(groups) != 3 or groups[0].items != expected:
        raise ValueError("semantic verifier overlay requires an ordered full first group")
    specialist_items = groups[1].items + groups[2].items
    if set(specialist_items) != set(expected) or len(specialist_items) != 24:
        raise ValueError("semantic verifier specialists must partition v1..v24")
