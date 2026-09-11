from pathlib import Path

from scripts.preflight_experiment import controlled_differences
from src.config import load_config


ROOT = Path(__file__).resolve().parents[1]


def test_sparse_serialization_configs_declare_only_output_policy_change() -> None:
    for base_name, candidate_name in (
        ("config.exp014-product-cards-v2-full200.yaml", "config.exp071-exp014-sparse-ve-serialization-fast-panel.yaml"),
        ("config.exp044-four-group-no-law-clean-prompt-full200.yaml", "config.exp072-exp044-sparse-ve-serialization-fast-panel.yaml"),
    ):
        base = load_config(ROOT / "configs" / base_name)
        candidate = load_config(ROOT / "configs" / candidate_name)
        assert set(controlled_differences(base, candidate)) == {"prompt.output_mode"}


def test_invalidated_config_cannot_be_loaded() -> None:
    invalid = ROOT / "configs/config.exp069-exp014-sparse-ve-fast-panel.yaml"
    try:
        load_config(invalid)
    except ValueError as exc:
        assert "invalidated" in str(exc)
    else:
        raise AssertionError("invalidated config must not be runnable")


def test_exp125_vonly_declares_only_output_contract_change() -> None:
    base = load_config(ROOT / "configs/config.exp125a-exact-baseline-ve-fast-panel.yaml")
    candidate = load_config(ROOT / "configs/config.exp125b-exact-baseline-vonly-fast-panel.yaml")
    assert set(controlled_differences(base, candidate)) == {"prompt.output_mode"}


def test_preflight_distinguishes_unset_from_explicit_null_group_override() -> None:
    base = load_config(ROOT / "configs" / "config.exp133-two-way-g02-fast-panel.yaml")
    candidate = load_config(ROOT / "configs" / "config.exp138-v9-source-coverage-fast-panel.yaml")
    differences = controlled_differences(base, candidate)
    key = "grouped_run.group_context_overrides.G03_specification_model.max_document_chars"
    assert differences[key] == {"base": "<unset>", "candidate": None}


def test_preflight_detects_postprocess_policy_change() -> None:
    base = load_config(ROOT / "configs/config.exp169-complete-source-2500-fast-panel-c4.yaml")
    candidate = load_config(
        ROOT / "configs/config.exp187-vonly-consensus-full-source-fast-panel-c4.yaml"
    )
    differences = controlled_differences(base, candidate)

    assert differences["postprocess.frozen_rule_set"] == {
        "base": "exp123_v1",
        "candidate": None,
    }


def test_exp192_declares_only_product_context_delivery_change() -> None:
    base = load_config(ROOT / "configs/config.exp169-complete-source-2500-fast-panel-c4.yaml")
    candidate = load_config(
        ROOT / "configs/config.exp192-product-condition-delivery-fast-panel-c4.yaml"
    )

    assert set(controlled_differences(base, candidate)) == {
        "prompt.competition_product_context_mode"
    }


def test_exp193_declares_only_v6_card_artifact_change() -> None:
    base = load_config(ROOT / "configs/config.exp169-complete-source-2500-fast-panel-c4.yaml")
    candidate = load_config(ROOT / "configs/config.exp193-v6-scope-card-fast-panel-c4.yaml")

    assert set(controlled_differences(base, candidate)) == {
        "prompt.decision_cards_path"
    }


def test_exp194_declares_only_organizer_input_semantics_change() -> None:
    base = load_config(ROOT / "configs/config.exp169-complete-source-2500-fast-panel-c4.yaml")
    candidate = load_config(
        ROOT / "configs/config.exp194-organizer-input-semantics-fast-panel-c4.yaml"
    )

    assert set(controlled_differences(base, candidate)) == {
        "prompt.organizer_input_semantics_mode"
    }


def test_exp198_declares_only_final_label_ownership_change() -> None:
    base = load_config(
        ROOT / "configs/config.exp197-human-readable-metadata-fast-panel-c4.yaml"
    )
    candidate = load_config(
        ROOT / "configs/config.exp198-model-owned-labels-fast-panel-c4.yaml"
    )

    assert set(controlled_differences(base, candidate)) == {
        "postprocess.frozen_rule_set"
    }
    assert candidate.frozen_rule_set is None
