from pathlib import Path

import pytest

from paper_pdf.config import load_config


def test_generic_local_override(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[browser]
headless = true
args = ["--no-proxy-server"]

[conversion]
backend = "pipeline"
""",
        encoding="utf-8",
    )
    config = load_config(config_path)
    assert config.browser.headless is True
    assert config.browser.args == ("--no-proxy-server",)
    assert config.conversion.backend == "pipeline"


def test_unknown_config_key_fails_fast(tmp_path: Path) -> None:
    path = tmp_path / "bad.toml"
    path.write_text("[browser]\nsecret_magic = true\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown configuration key"):
        load_config(path)
