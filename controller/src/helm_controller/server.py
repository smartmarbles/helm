"""Entry point for the Helm orchestration runtime controller.

Phase 1 scaffolding: ``main`` parses CLI arguments, resolves the effective
:class:`~helm_controller.config.ControllerConfig` (applying CLI overrides on top
of file/default precedence), and configures logging. The HTTP server itself is
implemented in Phase 3 (Task 3.0); this module is the stub it slots into.
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import os
from pathlib import Path

from helm_controller.config import (
    ConfigError,
    ControllerConfig,
    ResilienceConfig,
    load_config,
)
from helm_controller.hooks.decision_service import build_decision_handler
from helm_controller.transport.http_server import create_server

_LOGGER = logging.getLogger("helm_controller.server")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="helm-controller",
        description="Helm orchestration runtime controller — policy boundary for Copilot agent hooks.",
    )
    parser.add_argument(
        "--workspace",
        required=True,
        type=Path,
        help="Path to the workspace root the controller governs.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind (default: 0 = OS-assigned via config). Overrides config file [server] port.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Directory resolving agent_roles.yaml and tool_classes.yaml (default: package-bundled config).",
    )
    parser.add_argument(
        "--config-file",
        dest="config_file",
        type=Path,
        default=None,
        help="Path to helm-controller.toml (default: <workspace>/helm-controller.toml if present, else defaults).",
    )
    return parser


def _resolve_config(args: argparse.Namespace) -> ControllerConfig:
    workspace = args.workspace.resolve()
    config = load_config(workspace, args.config_file)
    if args.port is not None:
        config = dataclasses.replace(
            config, server=dataclasses.replace(config.server, port=args.port)
        )
    return config


def _write_port_file(port_file: Path, port: int) -> None:
    tmp = port_file.with_name(f"{port_file.name}.{os.getpid()}.tmp")
    tmp.write_text(str(port), encoding="utf-8")
    os.replace(tmp, port_file)


def _remove_port_file(port_file: Path) -> None:
    port_file.unlink(missing_ok=True)


def _log_resilience(resilience: ResilienceConfig) -> None:
    _LOGGER.info(
        "Resilience config: class_b_unavailable=%s auto_start=%s "
        "heal_budget_seconds=%s poll_interval_seconds=%s.",
        resilience.class_b_unavailable,
        resilience.auto_start,
        resilience.heal_budget_seconds,
        resilience.poll_interval_seconds,
    )


def _run_server(config: ControllerConfig, workspace: Path) -> int:
    decision_handler = build_decision_handler(workspace, config)
    server = create_server(
        config.server.bind_address,
        config.server.port,
        decision_handler,
    )
    bound_port = server.server_address[1]
    port_file = workspace / config.server.port_file
    _write_port_file(port_file, bound_port)
    _LOGGER.info(
        "Helm controller listening on %s:%d (port file %s).",
        config.server.bind_address,
        bound_port,
        port_file,
    )
    _log_resilience(config.resilience)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _LOGGER.info("Shutdown requested; stopping server.")
    finally:
        server.server_close()
        _remove_port_file(port_file)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        config = _resolve_config(args)
    except ConfigError as exc:
        logging.basicConfig(level=logging.ERROR)
        _LOGGER.error("Configuration error: %s", exc)
        return 2
    logging.basicConfig(level=config.pipeline.log_level)
    workspace = args.workspace.resolve()
    return _run_server(config, workspace)


if __name__ == "__main__":
    raise SystemExit(main())
