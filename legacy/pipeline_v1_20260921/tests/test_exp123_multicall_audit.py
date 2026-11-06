from scripts.audit_exp123_multicall import GROUPS, validate_groups
from src.schema import ITEMS


def test_exp123_multicall_groups_partition_every_item() -> None:
    validate_groups()
    assert tuple(item for group in GROUPS.values() for item in group) != ITEMS
    assert set(item for group in GROUPS.values() for item in group) == set(ITEMS)
