"""Tests for the controller startup path: config resolution, server run, entry."""

from __future__ import annotations

import logging
import runpy

import pytest

from helm_controller import server as server_module
from helm_controller.config import ResilienceConfig
from helm_controller.server import _log_resilience


def test_log_resilience_emits_resolved_values(caplog) -> None:
    resilience = ResilienceConfig(
        class_b_unavailable="hard_deny",
        auto_start=False,
        heal_budget_seconds=9.5,
        poll_interval_seconds=0.5,
    )

    with caplog.at_level(logging.INFO, logger="helm_controller.server"):
        _log_resilience(resilience)

    records = [r for r in caplog.records if r.name == "helm_controller.server"]
    assert len(records) == 1
    message = records[0].getMessage()
    assert "Resilience config:" in message
    assert "class_b_unavailable=hard_deny" in message
    assert "auto_start=False" in message
    assert "heal_budget_seconds=9.5" in message
    assert "poll_interval_seconds=0.5" in message


def test_log_resilience_emits_defaults(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="helm_controller.server"):
        _log_resilience(ResilienceConfig())

    message = caplog.records[-1].getMessage()
    assert "class_b_unavailable=actionable_deny" in message
    assert "auto_start=True" in message
    assert "heal_budget_seconds=6.0" in message
    assert "poll_interval_seconds=0.25" in message


class _FakeServer:
    """Stand-in for HookHTTPServer: serve_forever returns via KeyboardInterrupt."""

    def __init__(self, port: int = 54321) -> None:
        self.server_address = ("127.0.0.1", port)
        self.closed = False

    def serve_forever(self) -> None:
        raise KeyboardInterrupt

    def server_close(self) -> None:
        self.closed = True


def test_main_runs_server_and_manages_port_file(monkeypatch, tmp_path) -> None:
    captured: dict = {}

    def fake_create_server(bind, port, handler):
        captured["bind"] = bind
        captured["handler"] = handler
        return _FakeServer()

    monkeypatch.setattr(server_module, "create_server", fake_create_server)

    rc = server_module.main(["--workspace", str(tmp_path)])

    assert rc == 0
    assert captured["bind"] == "127.0.0.1"
    assert callable(captured["handler"])
    # Port file written during run is removed by the finally block.
    assert not (tmp_path / ".helm-controller.port").exists()


def test_main_applies_port_override(monkeypatch, tmp_path) -> None:
    seen: dict = {}

    def fake_create_server(bind, port, handler):
        seen["port"] = port
        return _FakeServer(port=port or 0)

    monkeypatch.setattr(server_module, "create_server", fake_create_server)

    rc = server_module.main(["--workspace", str(tmp_path), "--port", "8123"])

    assert rc == 0
    assert seen["port"] == 8123


def test_main_returns_2_on_config_error(monkeypatch, tmp_path) -> None:
    bad_toml = tmp_path / "helm-controller.toml"
    bad_toml.write_text("this is = = not valid toml", encoding="utf-8")

    def fake_create_server(*_args, **_kwargs):  # pragma: no cover - must not run
        raise AssertionError("server must not start on config error")

    monkeypatch.setattr(server_module, "create_server", fake_create_server)

    rc = server_module.main(
        ["--workspace", str(tmp_path), "--config-file", str(bad_toml)]
    )

    assert rc == 2


def _argv_for_config_error(tmp_path) -> list[str]:
    bad_toml = tmp_path / "helm-controller.toml"
    bad_toml.write_text("= = invalid", encoding="utf-8")
    return ["helm-controller", "--workspace", str(tmp_path), "--config-file", str(bad_toml)]


def test_server_module_guard_invokes_main(monkeypatch, tmp_path) -> None:
    # Run server.py as __main__ so the `if __name__ == "__main__"` guard fires;
    # the ConfigError argv exits early (rc 2) without binding a socket.
    monkeypatch.setattr("sys.argv", _argv_for_config_error(tmp_path))
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("helm_controller.server", run_name="__main__")
    assert exc.value.code == 2


def test_package_dunder_main_invokes_main(monkeypatch, tmp_path) -> None:
    # Run the package as __main__ (python -m helm_controller) so __main__.py's
    # guard executes the import-and-dispatch line.
    monkeypatch.setattr("sys.argv", _argv_for_config_error(tmp_path))
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("helm_controller", run_name="__main__")
    assert exc.value.code == 2


def test_dunder_main_import_does_not_run_guard() -> None:
    # Importing the module under its real name (not __main__) takes the guard's
    # false branch: main must NOT be invoked on a plain import.
    import helm_controller.__main__ as dunder_main

    assert dunder_main.main is server_module.main
