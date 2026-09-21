import pytest

from src.legal_groups import (
    ABSENCE_PRESENCE_ITEM_GROUPS,
    ABSENCE_PRESENCE_CONSISTENCY_ITEM_GROUPS,
    DOCUMENT_RESTRICTIONS_TWO_WAY_GROUPS,
    DOCUMENT_RESTRICTIONS_OVERLAY_GROUPS,
    SEMANTIC_VERIFIER_OVERLAY_GROUPS,
    DOCUMENT_RESTRICTIONS_V9_SOURCE_GROUPS,
    FOUR_WAY_ITEM_GROUPS,
    THREE_WAY_ITEM_GROUPS,
    groups_for_scheme,
    validate_groups,
    validate_document_restrictions_overlay,
    validate_semantic_verifier_overlay,
)


def test_four_way_groups_partition_all_items_once() -> None:
    validate_groups(FOUR_WAY_ITEM_GROUPS)
    assert [len(group.items) for group in FOUR_WAY_ITEM_GROUPS] == [5, 5, 9, 5]
    assert groups_for_scheme("four_way") == FOUR_WAY_ITEM_GROUPS


def test_unknown_grouping_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown item grouping"):
        groups_for_scheme("unknown")


def test_three_way_groups_partition_all_items_once() -> None:
    validate_groups(THREE_WAY_ITEM_GROUPS)
    assert [len(group.items) for group in THREE_WAY_ITEM_GROUPS] == [10, 9, 5]


def test_absence_presence_groups_partition_items_and_isolate_absence() -> None:
    validate_groups(ABSENCE_PRESENCE_ITEM_GROUPS)
    assert groups_for_scheme("absence_presence_v1") == ABSENCE_PRESENCE_ITEM_GROUPS
    assert ABSENCE_PRESENCE_ITEM_GROUPS[1].items == ("v10", "v11", "v16", "v18", "v20")


def test_consistency_three_way_group_isolates_v24() -> None:
    validate_groups(ABSENCE_PRESENCE_CONSISTENCY_ITEM_GROUPS)
    assert groups_for_scheme("absence_presence_consistency_v1") == ABSENCE_PRESENCE_CONSISTENCY_ITEM_GROUPS
    assert ABSENCE_PRESENCE_CONSISTENCY_ITEM_GROUPS[2].items == ("v24",)
    assert groups_for_scheme("three_way") == THREE_WAY_ITEM_GROUPS


def test_document_restrictions_two_way_groups_are_disjoint_complete_partition() -> None:
    validate_groups(DOCUMENT_RESTRICTIONS_TWO_WAY_GROUPS)
    assert groups_for_scheme("document_restrictions_two_way_v1") == DOCUMENT_RESTRICTIONS_TWO_WAY_GROUPS
    assert DOCUMENT_RESTRICTIONS_TWO_WAY_GROUPS[1].items == ("v6", "v7", "v8", "v9", "v19")


def test_document_restrictions_overlay_is_fixed_and_ordered() -> None:
    validate_document_restrictions_overlay(DOCUMENT_RESTRICTIONS_OVERLAY_GROUPS)
    assert groups_for_scheme("document_restrictions_overlay_v1") == DOCUMENT_RESTRICTIONS_OVERLAY_GROUPS
    assert DOCUMENT_RESTRICTIONS_OVERLAY_GROUPS[0].items == tuple(f"v{index}" for index in range(1, 25))
    assert DOCUMENT_RESTRICTIONS_OVERLAY_GROUPS[1].items == ("v6", "v7", "v8", "v9", "v19")


def test_semantic_verifier_overlay_has_full_control_and_disjoint_specialists() -> None:
    validate_semantic_verifier_overlay(SEMANTIC_VERIFIER_OVERLAY_GROUPS)
    assert groups_for_scheme("semantic_verifier_overlay_v1") == SEMANTIC_VERIFIER_OVERLAY_GROUPS
    assert len(SEMANTIC_VERIFIER_OVERLAY_GROUPS[0].items) == 24
    assert len(SEMANTIC_VERIFIER_OVERLAY_GROUPS[1].items) == 14
    assert len(SEMANTIC_VERIFIER_OVERLAY_GROUPS[2].items) == 10


def test_v9_source_groups_are_disjoint_complete_partition() -> None:
    validate_groups(DOCUMENT_RESTRICTIONS_V9_SOURCE_GROUPS)
    assert groups_for_scheme("document_restrictions_v9_source_v1") == DOCUMENT_RESTRICTIONS_V9_SOURCE_GROUPS
    assert DOCUMENT_RESTRICTIONS_V9_SOURCE_GROUPS[2].items == ("v9",)
