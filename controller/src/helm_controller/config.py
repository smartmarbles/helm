"""Configuration loading for the Helm orchestration runtime controller.

Config format is TOML, parsed with the stdlib :mod:`tomllib` (Python 3.13+).
Precedence is CLI args > config file > built-in defaults. The CLI layer is
applied by :mod:`helm_controller.server`; this module covers the file-versus-
defaults resolution and produces an immutable :class:`ControllerConfig`.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_FILENAME = "helm-controller.toml"


class ConfigError(Exception):
    """Raised when a config file cannot be read or parsed."""


@dataclass(frozen=True)
class ServerConfig:
    bind_address: str = "127.0.0.1"
    port: int = 0
    port_file: str = ".helm-controller.port"


@dataclass(frozen=True)
class StoreConfig:
    db_path: str = ".helm-controller.db"
    busy_timeout_ms: int = 5000
    fallback_timeout_ms: int = 100


@dataclass(frozen=True)
class LockingConfig:
    lock_ttl_seconds: int = 1800


@dataclass(frozen=True)
class ScrConfig:
    root_dir: str = ".scr"


@dataclass(frozen=True)
class PipelineConfig:
    log_level: str = "INFO"


@dataclass(frozen=True)
class ResilienceConfig:
    class_b_unavailable: str = "actionable_deny"
    auto_start: bool = True
    heal_budget_seconds: float = 6.0
    poll_interval_seconds: float = 0.25


@dataclass(frozen=True)
class ControllerConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    store: StoreConfig = field(default_factory=StoreConfig)
    locking: LockingConfig = field(default_factory=LockingConfig)
    scr: ScrConfig = field(default_factory=ScrConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    resilience: ResilienceConfig = field(default_factory=ResilienceConfig)


_SECTION_KEYS: dict[str, tuple[str, ...]] = {
    "server": ("bind_address", "port", "port_file"),
    "store": ("db_path", "busy_timeout_ms", "fallback_timeout_ms"),
    "locking": ("lock_ttl_seconds",),
    "scr": ("root_dir",),
    "pipeline": ("log_level",),
    "resilience": (
        "class_b_unavailable",
        "auto_start",
        "heal_budget_seconds",
        "poll_interval_seconds",
    ),
}


def load_config(workspace: Path, config_file: Path | None) -> ControllerConfig:
    """Resolve a :class:`ControllerConfig` from an optional TOML file.

    When ``config_file`` is ``None`` the loader looks for
    ``<workspace>/helm-controller.toml``; if that file is absent the built-in
    defaults are returned. When ``config_file`` is provided it must exist.
    """
    path = _resolve_path(workspace, config_file)
    if path is None:
        return ControllerConfig()
    return _from_mapping(_read_toml(path))


def _resolve_path(workspace: Path, config_file: Path | None) -> Path | None:
    if config_file is not None:
        if not config_file.is_file():
            raise ConfigError(f"Config file not found: {config_file}")
        return config_file
    candidate = workspace / DEFAULT_CONFIG_FILENAME
    if candidate.is_file():
        return candidate
    return None


def _read_toml(path: Path) -> Mapping[str, Any]:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"Cannot read config file {path}: {exc}") from exc


def _from_mapping(raw: Mapping[str, Any]) -> ControllerConfig:
    defaults = ControllerConfig()
    return ControllerConfig(
        server=replace(defaults.server, **_pick(raw, "server")),
        store=replace(defaults.store, **_pick(raw, "store")),
        locking=replace(defaults.locking, **_pick(raw, "locking")),
        scr=replace(defaults.scr, **_pick(raw, "scr")),
        pipeline=replace(defaults.pipeline, **_pick(raw, "pipeline")),
        resilience=replace(defaults.resilience, **_pick(raw, "resilience")),
    )


def _pick(raw: Mapping[str, Any], section: str) -> dict[str, Any]:
    values = raw.get(section, {})
    return {key: values[key] for key in _SECTION_KEYS[section] if key in values}
