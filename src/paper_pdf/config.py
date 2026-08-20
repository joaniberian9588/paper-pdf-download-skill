"""Generic public configuration with gitignored local overrides."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import user_config_path, user_data_path


@dataclass(slots=True)
class NetworkConfig:
    timeout_seconds: int = 60
    verify_tls: bool = True
    user_agent: str = "paper-pdf-download-skill/0.1 (+https://github.com/wxt18757928900-lgtm/paper-pdf-download-skill)"


@dataclass(slots=True)
class BrowserConfig:
    enabled: bool = True
    profile_dir: Path = field(
        default_factory=lambda: user_data_path("paper-pdf-download") / "profiles"
    )
    headless: bool = True
    humanize: bool = True
    auto_update: bool = False
    args: tuple[str, ...] = ()
    navigation_timeout_seconds: int = 90
    candidate_timeout_seconds: int = 25
    max_candidate_urls: int = 12
    settle_seconds: float = 2.0


@dataclass(slots=True)
class ApiConfig:
    unpaywall_email: str = ""
    elsevier_api_key_env: str = "ELSEVIER_API_KEY"
    elsevier_inst_token_env: str = "ELSEVIER_INST_TOKEN"


@dataclass(slots=True)
class ConversionConfig:
    mineru_command: str = "mineru"
    mineru_open_api_command: str = "mineru-open-api"
    backend: str = "pipeline"
    language: str = "ch"
    min_markdown_chars: int = 100


@dataclass(slots=True)
class AppConfig:
    network: NetworkConfig = field(default_factory=NetworkConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    apis: ApiConfig = field(default_factory=ApiConfig)
    conversion: ConversionConfig = field(default_factory=ConversionConfig)
    config_path: Path | None = None


def default_config_path() -> Path:
    return user_config_path("paper-pdf-download") / "config.toml"


def load_config(path: Path | None = None) -> AppConfig:
    config = AppConfig()
    selected = path
    if selected is None and os.environ.get("PAPER_PDF_CONFIG"):
        selected = Path(os.environ["PAPER_PDF_CONFIG"])
    if selected is None:
        candidate = default_config_path()
        selected = candidate if candidate.exists() else None
    if selected is None:
        return config

    selected = selected.expanduser().resolve()
    data = tomllib.loads(selected.read_text(encoding="utf-8"))
    _apply_section(config.network, data.get("network", {}))
    _apply_section(config.browser, data.get("browser", {}), path_fields={"profile_dir"})
    _apply_section(config.apis, data.get("apis", {}))
    _apply_section(config.conversion, data.get("conversion", {}))
    config.config_path = selected
    return config


def _apply_section(
    target: object, values: dict[str, object], path_fields: set[str] | None = None
) -> None:
    path_fields = path_fields or set()
    for key, value in values.items():
        if not hasattr(target, key):
            raise ValueError(f"Unknown configuration key: {type(target).__name__}.{key}")
        if key == "args":
            value = tuple(str(item) for item in value)  # type: ignore[arg-type]
        elif key in path_fields:
            value = Path(str(value)).expanduser()
        setattr(target, key, value)


def configured_elsevier_credentials(config: AppConfig) -> tuple[str, str]:
    key = os.environ.get(config.apis.elsevier_api_key_env, "").strip()
    token = os.environ.get(config.apis.elsevier_inst_token_env, "").strip()
    return key, token
