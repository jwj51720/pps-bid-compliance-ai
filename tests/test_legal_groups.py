import pytest

from src.legal_groups import (
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
    assert groups_for_scheme("three_way") == THREE_WAY_ITEM_GROUPS
