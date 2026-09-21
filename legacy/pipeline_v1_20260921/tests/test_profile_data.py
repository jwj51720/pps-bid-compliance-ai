from pathlib import Path


def test_profile_data_script_accepts_repository_config_option() -> None:
    source = Path("scripts/profile_data.py").read_text(encoding="utf-8")

    assert '"--config"' in source
    assert "load_config(args.config)" in source
    assert "config.data.input_path" in source
    assert "config.data.labels_path" in source
