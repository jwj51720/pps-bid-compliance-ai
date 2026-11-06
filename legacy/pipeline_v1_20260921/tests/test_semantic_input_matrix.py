from pathlib import Path

from scripts.audit_semantic_input_matrix import parse_contract
from src.schema import ITEMS


def test_semantic_contract_has_every_item_once() -> None:
    contract = parse_contract(Path("docs/semantic_input_contract_v1.md"))
    assert tuple(contract) == ITEMS
    assert all(entry["condition"] and entry["zero_condition"] for entry in contract.values())


def test_semantic_contract_records_source_and_notice_scope() -> None:
    contract = parse_contract(Path("docs/semantic_input_contract_v1.md"))
    assert "CSV" in contract["v10"]["required_facts"]
    assert "All supplied documents" in contract["v20"]["required_notice_scope"]
