"""Tests for the TOML config loader (file-versus-defaults resolution)."""

from __future__ import annotations

import pytest

from helm_controller.config import (
    ConfigError,
    ControllerConfig,
    DEFAULT_CONFIG_FILENAME,
    load_config,
)
from helm_controller.config import _read_toml

_FULL_TOML = """\
[server]
bind_address = "0.0.0.0"
port = 9000
port_file = "custom.port"

[store]
db_path = "custom.db"
busy_timeout_ms = 1234
fallback_timeout_ms = 50

[locking]
lock_ttl_seconds = 3600

[scr]
root_dir = "custom-scr"

[pipeline]
log_level = "DEBUG"
"""

_PARTIAL_TOML = """\
[server]
port = 9000

[locking]
lock_ttl_seconds = 7200
"""


def test_load_config_file_present_all_keys_overridden(tmp_path) -> None:
    cfg_path = tmp_path / "helm-controller.toml"
    cfg_path.write_text(_FULL_TOML, encoding="utf-8")

    cfg = load_config(tmp_path, cfg_path)

    assert cfg.server.bind_address == "0.0.0.0"
    assert cfg.server.port == 9000
    assert cfg.server.port_file == "custom.port"
    assert cfg.store.db_path == "custom.db"
    assert cfg.store.busy_timeout_ms == 1234
    assert cfg.store.fallback_timeout_ms == 50
    assert cfg.locking.lock_ttl_seconds == 3600
    assert cfg.scr.root_dir == "custom-scr"
    assert cfg.pipeline.log_level == "DEBUG"


def test_load_config_file_absent_returns_defaults(tmp_path) -> None:
    cfg = load_config(tmp_path, None)
    assert cfg == ControllerConfig()


def test_load_config_default_filename_picked_up(tmp_path) -> None:
    (tmp_path / DEFAULT_CONFIG_FILENAME).write_text(_FULL_TOML, encoding="utf-8")
    cfg = load_config(tmp_path, None)
    assert cfg.server.port == 9000


def test_load_config_partial_keys_mix_overrides_and_defaults(tmp_path) -> None:
    cfg_path = tmp_path / "partial.toml"
    cfg_path.write_text(_PARTIAL_TOML, encoding="utf-8")

    cfg = load_config(tmp_path, cfg_path)

    # Overridden keys.
    assert cfg.server.port == 9000
    assert cfg.locking.lock_ttl_seconds == 7200
    # Sibling key in a present section falls back to default.
    assert cfg.server.bind_address == "127.0.0.1"
    assert cfg.server.port_file == ".helm-controller.port"
    # Entirely absent sections fall back to defaults.
    assert cfg.store == ControllerConfig().store
    assert cfg.scr == ControllerConfig().scr
    assert cfg.pipeline == ControllerConfig().pipeline


def test_load_config_explicit_file_missing_raises(tmp_path) -> None:
    missing = tmp_path / "nope.toml"
    with pytest.raises(ConfigError):
        load_config(tmp_path, missing)


def test_load_config_invalid_toml_raises_config_error(tmp_path) -> None:
    cfg_path = tmp_path / "bad.toml"
    cfg_path.write_text("this is = = not valid toml", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(tmp_path, cfg_path)


def test_read_toml_os_error_reraised_as_config_error(tmp_path) -> None:
    # Opening a directory as a file raises OSError, exercising the OSError branch.
    with pytest.raises(ConfigError):
        _read_toml(tmp_path)


def test_load_config_resilience_defaults_when_section_absent(tmp_path) -> None:
    cfg = load_config(tmp_path, None)
    assert cfg.resilience == ControllerConfig().resilience
    assert cfg.resilience.class_b_unavailable == "actionable_deny"
    assert cfg.resilience.auto_start is True


def test_load_config_resilience_section_overrides(tmp_path) -> None:
    cfg_path = tmp_path / "helm-controller.toml"
    cfg_path.write_text(
        "[resilience]\n"
        'class_b_unavailable = "strict_deny"\n'
        "auto_start = false\n"
        "heal_budget_seconds = 3.5\n"
        "poll_interval_seconds = 0.1\n",
        encoding="utf-8",
    )

    cfg = load_config(tmp_path, cfg_path)

    assert cfg.resilience.class_b_unavailable == "strict_deny"
    assert cfg.resilience.auto_start is False
    assert cfg.resilience.heal_budget_seconds == 3.5
    assert cfg.resilience.poll_interval_seconds == 0.1
