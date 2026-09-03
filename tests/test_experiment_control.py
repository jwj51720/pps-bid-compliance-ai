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
