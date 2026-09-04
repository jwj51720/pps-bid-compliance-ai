import pytest

from src.legal_groups import (
    ABSENCE_PRESENCE_ITEM_GROUPS,
    ABSENCE_PRESENCE_CONSISTENCY_ITEM_GROUPS,
    FOUR_WAY_ITEM_GROUPS,
    THREE_WAY_ITEM_GROUPS,
    groups_for_scheme,
    validate_groups,
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
