"""100%-branch tests for the stdlib hook resilience helper (`_helm_hook`).

Every external side effect is injected through a fake :class:`Env` so the
event-class × availability matrix, the self-heal state machine, the suspend
short-circuit, the actionable-deny contract, and the config reader are all
exercised deterministically — no real sockets, subprocess spawns, or sleeps.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import time
import types
from pathlib import Path

import pytest

_HOOKS_DIR = Path(__file__).resolve().parents[3] / ".github" / "hooks"
sys.path.insert(0, str(_HOOKS_DIR))
import _helm_hook as H  # noqa: E402


# --- Event specs mirroring the eight shim declarations --------------------

SPECS = {
    "PreToolUse": H.EventSpec(
        "PreToolUse",
        "B",
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        },
        "permission",
    ),
    "PostToolUse": H.EventSpec("PostToolUse", "B", {}, "block"),
    "SubagentStart": H.EventSpec("SubagentStart", "B", {}, "common"),
    "SubagentStop": H.EventSpec("SubagentStop", "B", {}, "block"),
    "Stop": H.EventSpec("Stop", "B", {}, "block"),
    "SessionStart": H.EventSpec("SessionStart", "A", {}, "common"),
    "UserPromptSubmit": H.EventSpec("UserPromptSubmit", "A", {}, "common"),
    "PreCompact": H.EventSpec("PreCompact", "A", {"continue": True}, "common"),
}


# --- Injectable fake environment ------------------------------------------


class Env:
    """Holds configurable seam state; `deps()` packages it as a `Deps`."""

    def __init__(self) -> None:
        self.config = H.ResilienceConfig()
        self.suspend = False
        self.ports: list[int | None] = [1234]
        self.posts: list[str | None] = ["{}"]
        self.nows: list[float] = [0.0]
        self.lock_results: list[object | None] = [object()]
        self.reclaim = False
        self.spawns = 0
        self.releases = 0
        self.slept: list[float] = []
        self.logs: list[str] = []
        self.posted_payloads: list[str] = []

    @staticmethod
    def _next(values: list):
        return values.pop(0) if len(values) > 1 else values[0]

    def read_config(self, root):
        return self.config

    def suspend_exists(self, root):
        return self.suspend

    def read_port(self, root):
        return self._next(self.ports)

    def post(self, root, port, payload):
        self.posted_payloads.append(payload)
        return self._next(self.posts)

    def now(self):
        return self._next(self.nows)

    def sleep(self, seconds):
        self.slept.append(seconds)

    def spawn(self, root):
        self.spawns += 1

    def acquire_lock(self, root):
        return self._next(self.lock_results)

    def release_lock(self, root, token):
        self.releases += 1

    def reclaim_stale_lock(self, root):
        return self.reclaim

    def log(self, root, message):
        self.logs.append(message)

    def deps(self) -> H.Deps:
        return H.Deps(
            read_config=self.read_config,
            suspend_exists=self.suspend_exists,
            read_port=self.read_port,
            post=self.post,
            now=self.now,
            sleep=self.sleep,
            spawn=self.spawn,
            acquire_lock=self.acquire_lock,
            release_lock=self.release_lock,
            reclaim_stale_lock=self.reclaim_stale_lock,
            log=self.log,
        )


def run_spec(spec: H.EventSpec, env: Env, payload: str = "{}") -> str:
    out = io.StringIO()
    stdin = types.SimpleNamespace(read=lambda: payload.encode("utf-8"))
    rc = H.run(spec, deps=env.deps(), stdin=stdin, stdout=out)
    assert rc == 0
    return out.getvalue()


# --- Class A: responded ----------------------------------------------------


def test_class_a_responded_allow_honored_verbatim() -> None:
    env = Env()
    env.posts = ['{"continue": true}']
    out = run_spec(SPECS["UserPromptSubmit"], env)
    assert out == '{"continue": true}'


def test_class_a_responded_deny_degrades_to_pass() -> None:
    env = Env()
    env.posts = ['{"continue": false, "stopReason": "policy"}']
    out = run_spec(SPECS["UserPromptSubmit"], env)
    assert json.loads(out) == {}  # event-native proceed, NOT the deny
    assert any(H.MARKER_NOTICE in line and "degraded" in line for line in env.logs)


def test_class_a_responded_deny_degrade_precompact_stays_continue_true() -> None:
    env = Env()
    env.posts = ['{"continue": false, "stopReason": "policy"}']
    out = run_spec(SPECS["PreCompact"], env)
    assert json.loads(out) == {"continue": True}


# --- Class A: unavailable --------------------------------------------------


def test_class_a_unavailable_passes() -> None:
    env = Env()
    env.config = H.ResilienceConfig(auto_start=False)
    env.ports = [None]
    out = run_spec(SPECS["SessionStart"], env)
    assert json.loads(out) == {}
    assert env.spawns == 0
    assert any(H.MARKER_NOTICE in line for line in env.logs)


# --- Class B: responded ----------------------------------------------------


def test_class_b_responded_allow_verbatim() -> None:
    env = Env()
    allow = json.dumps(SPECS["PreToolUse"].allow)
    env.posts = [allow]
    out = run_spec(SPECS["PreToolUse"], env)
    assert out == allow


def test_class_b_responded_deny_verbatim_no_marker() -> None:
    env = Env()
    deny = (
        '{"hookSpecificOutput": {"hookEventName": "PreToolUse", '
        '"permissionDecision": "deny", "permissionDecisionReason": "PC-004 policy"}}'
    )
    env.posts = [deny]
    out = run_spec(SPECS["PreToolUse"], env)
    assert out == deny
    assert H.MARKER_UNAVAILABLE not in out


# --- Class B: unavailable --------------------------------------------------


def test_class_b_unavailable_actionable_deny_default() -> None:
    env = Env()
    env.config = H.ResilienceConfig(auto_start=False)
    env.ports = [None]
    out = run_spec(SPECS["PreToolUse"], env)
    reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
    assert reason.startswith(H.MARKER_UNAVAILABLE)
    assert "action=offer-start" in reason
    assert "event=PreToolUse" in reason
    assert "heal_attempted=false" in reason


def test_class_b_unavailable_strict_deny_omits_marker() -> None:
    env = Env()
    env.config = H.ResilienceConfig(
        class_b_unavailable="strict_deny", auto_start=False
    )
    env.ports = [None]
    out = run_spec(SPECS["Stop"], env)
    payload = json.loads(out)
    assert payload["decision"] == "block"
    assert H.MARKER_UNAVAILABLE not in payload["reason"]
    assert "action=offer-start" not in payload["reason"]


# --- Suspend short-circuit -------------------------------------------------


def test_suspend_class_b_passes_with_marker_no_contact() -> None:
    env = Env()
    env.suspend = True
    out = run_spec(SPECS["PreToolUse"], env)
    hso = json.loads(out)["hookSpecificOutput"]
    assert hso["permissionDecision"] == "allow"
    assert H.MARKER_SUSPENDED in hso["permissionDecisionReason"]
    assert env.posted_payloads == []  # no controller POST
    assert env.spawns == 0  # no self-heal
    assert env.slept == []
    assert any(H.MARKER_SUSPENDED in line for line in env.logs)


def test_suspend_class_a_passes_log_only() -> None:
    env = Env()
    env.suspend = True
    out = run_spec(SPECS["UserPromptSubmit"], env)
    assert json.loads(out) == {}
    assert env.posted_payloads == []
    assert any(H.MARKER_SUSPENDED in line for line in env.logs)


# --- Self-heal state machine ----------------------------------------------


def test_self_heal_success_then_retry_honored() -> None:
    env = Env()
    env.ports = [None, 5000]  # initial unavailable, then bound after spawn
    env.posts = ['{"continue": true}']
    env.nows = [0.0, 1.0]
    out = run_spec(SPECS["SubagentStart"], env)
    assert out == '{"continue": true}'
    assert env.spawns == 1
    assert env.releases == 1


def test_self_heal_binds_but_retry_post_fails_actionable_deny() -> None:
    env = Env()
    env.ports = [None, 5000]
    env.posts = [None]  # retry POST still fails
    env.nows = [0.0, 1.0]
    out = run_spec(SPECS["Stop"], env)
    reason = json.loads(out)["reason"]
    assert reason.startswith(H.MARKER_UNAVAILABLE)
    assert "heal_attempted=true" in reason
    assert env.spawns == 1


def test_self_heal_no_bind_within_budget_actionable_deny() -> None:
    env = Env()
    env.ports = [None]  # never binds
    env.posts = [None]
    env.nows = [0.0, 1.0, 7.0]  # deadline=6: one poll iteration then timeout
    out = run_spec(SPECS["PostToolUse"], env)
    reason = json.loads(out)["reason"]
    assert reason.startswith(H.MARKER_UNAVAILABLE)
    assert "heal_attempted=true" in reason
    assert env.spawns == 1
    assert env.slept == [env.config.poll_interval_seconds]


def test_self_heal_lock_contention_polls_no_spawn() -> None:
    env = Env()
    env.ports = [None, 5000]  # another wrapper's controller binds
    env.posts = ['{"continue": true}']
    env.nows = [0.0, 1.0]
    env.lock_results = [None]  # lock held by another, reclaim says live
    env.reclaim = False
    out = run_spec(SPECS["SubagentStart"], env)
    assert out == '{"continue": true}'
    assert env.spawns == 0
    assert env.releases == 0


def test_self_heal_stale_lock_reclaimed_then_spawn() -> None:
    env = Env()
    env.ports = [None, 5000]
    env.posts = ['{"continue": true}']
    env.nows = [0.0, 1.0]
    env.lock_results = [None, object()]  # first contended, reclaimed, then acquired
    env.reclaim = True
    out = run_spec(SPECS["SubagentStart"], env)
    assert out == '{"continue": true}'
    assert env.spawns == 1
    assert env.releases == 1


def test_auto_start_disabled_skips_spawn() -> None:
    env = Env()
    env.config = H.ResilienceConfig(auto_start=False)
    env.ports = [None]
    out = run_spec(SPECS["SubagentStop"], env)
    reason = json.loads(out)["reason"]
    assert "heal_attempted=false" in reason
    assert env.spawns == 0


# --- Response classification ----------------------------------------------


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("not json", False),
        ("[]", False),
        ('{"continue": false}', True),
        ('{"decision": "block"}', True),
        ('{"hookSpecificOutput": {"permissionDecision": "deny"}}', True),
        ('{"continue": true}', False),
        ('{"hookSpecificOutput": {"permissionDecision": "allow"}}', False),
    ],
)
def test_response_is_deny(body: str, expected: bool) -> None:
    assert H._response_is_deny(body) is expected


# --- Per-event wire shapes -------------------------------------------------


@pytest.mark.parametrize("name", list(SPECS))
def test_build_pass_and_deny_shapes(name: str) -> None:
    spec = SPECS[name]
    passed = H._build_pass(spec)
    assert passed == spec.allow
    deny = H._build_deny(spec, "because")
    if spec.deny_shape == "permission":
        assert deny["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert deny["hookSpecificOutput"]["permissionDecisionReason"] == "because"
    elif spec.deny_shape == "block":
        assert deny == {"decision": "block", "reason": "because"}
    else:
        assert deny == {"continue": False, "stopReason": "because"}


def test_build_pass_embeds_notice_only_for_permission_shape() -> None:
    permission = H._build_pass(SPECS["PreToolUse"], notice="note")
    assert (
        permission["hookSpecificOutput"]["permissionDecisionReason"] == "note"
    )
    common = H._build_pass(SPECS["UserPromptSubmit"], notice="note")
    assert "systemMessage" not in common  # log-only for common-output events
    assert common == {}


# --- Last-resort safe fallback --------------------------------------------


def _raising_deps(env: Env) -> H.Deps:
    deps = env.deps()
    return H.Deps(
        read_config=lambda root: (_ for _ in ()).throw(RuntimeError("boom")),
        suspend_exists=deps.suspend_exists,
        read_port=deps.read_port,
        post=deps.post,
        now=deps.now,
        sleep=deps.sleep,
        spawn=deps.spawn,
        acquire_lock=deps.acquire_lock,
        release_lock=deps.release_lock,
        reclaim_stale_lock=deps.reclaim_stale_lock,
        log=deps.log,
    )


def test_safe_fallback_class_a_passes_on_unexpected_error() -> None:
    out = io.StringIO()
    stdin = types.SimpleNamespace(read=lambda: b"{}")
    H.run(SPECS["PreCompact"], deps=_raising_deps(Env()), stdin=stdin, stdout=out)
    assert json.loads(out.getvalue()) == {"continue": True}


def test_safe_fallback_class_b_denies_on_unexpected_error() -> None:
    out = io.StringIO()
    stdin = types.SimpleNamespace(read=lambda: b"{}")
    H.run(SPECS["Stop"], deps=_raising_deps(Env()), stdin=stdin, stdout=out)
    payload = json.loads(out.getvalue())
    assert payload["decision"] == "block"
    assert H.MARKER_UNAVAILABLE not in payload["reason"]


# --- run() default seam wiring --------------------------------------------


def test_run_uses_default_seams(monkeypatch) -> None:
    env = Env()
    env.posts = ['{"continue": true}']
    monkeypatch.setattr(H, "default_deps", lambda: env.deps())
    buf = io.StringIO()
    fake_stdin = types.SimpleNamespace(
        buffer=types.SimpleNamespace(read=lambda: b"{}")
    )
    monkeypatch.setattr(sys, "stdin", fake_stdin)
    monkeypatch.setattr(sys, "stdout", buf)
    rc = H.run(SPECS["UserPromptSubmit"])
    assert rc == 0
    assert buf.getvalue() == '{"continue": true}'


def test_default_deps_constructs_real_callables() -> None:
    deps = H.default_deps()
    assert isinstance(deps, H.Deps)
    assert callable(deps.post)
    assert callable(deps.spawn)
    assert deps.now is time.monotonic


# --- Default config reader (secure-default collapse) ----------------------


def test_read_config_absent_file_defaults(tmp_path) -> None:
    assert H._default_read_config(tmp_path) == H.ResilienceConfig()


def test_read_config_malformed_toml_defaults(tmp_path) -> None:
    (tmp_path / H.CONFIG_FILE).write_text("= = bad", encoding="utf-8")
    assert H._default_read_config(tmp_path) == H.ResilienceConfig()


def test_read_config_non_dict_section_defaults(tmp_path) -> None:
    (tmp_path / H.CONFIG_FILE).write_text(
        'resilience = "nope"\n', encoding="utf-8"
    )
    assert H._default_read_config(tmp_path) == H.ResilienceConfig()


def test_read_config_all_keys_valid_overrides(tmp_path) -> None:
    (tmp_path / H.CONFIG_FILE).write_text(
        "[resilience]\n"
        'class_b_unavailable = "strict_deny"\n'
        "auto_start = false\n"
        "heal_budget_seconds = 4\n"
        "poll_interval_seconds = 0.5\n",
        encoding="utf-8",
    )
    cfg = H._default_read_config(tmp_path)
    assert cfg.class_b_unavailable == "strict_deny"
    assert cfg.auto_start is False
    assert cfg.heal_budget_seconds == 4.0
    assert cfg.poll_interval_seconds == 0.5


def test_read_config_invalid_values_collapse_to_defaults(tmp_path) -> None:
    (tmp_path / H.CONFIG_FILE).write_text(
        "[resilience]\n"
        'class_b_unavailable = "bogus"\n'
        'auto_start = "yes"\n'
        "heal_budget_seconds = true\n"
        'poll_interval_seconds = "fast"\n',
        encoding="utf-8",
    )
    cfg = H._default_read_config(tmp_path)
    assert cfg == H.ResilienceConfig()


def test_read_config_non_positive_numbers_default(tmp_path) -> None:
    (tmp_path / H.CONFIG_FILE).write_text(
        "[resilience]\nheal_budget_seconds = 0\npoll_interval_seconds = -1\n",
        encoding="utf-8",
    )
    cfg = H._default_read_config(tmp_path)
    assert cfg.heal_budget_seconds == H.ResilienceConfig.heal_budget_seconds
    assert cfg.poll_interval_seconds == H.ResilienceConfig.poll_interval_seconds


# --- Default suspend / port / log seams -----------------------------------


def test_default_suspend_exists(tmp_path) -> None:
    assert H._default_suspend_exists(tmp_path) is False
    (tmp_path / H.SUSPEND_FILE).write_text("", encoding="utf-8")
    assert H._default_suspend_exists(tmp_path) is True


def test_default_read_port_valid_missing_and_malformed(tmp_path) -> None:
    assert H._default_read_port(tmp_path) is None  # missing
    (tmp_path / H.PORT_FILE).write_text("not-a-port", encoding="utf-8")
    assert H._default_read_port(tmp_path) is None  # malformed
    (tmp_path / H.PORT_FILE).write_text("5123\n", encoding="utf-8")
    assert H._default_read_port(tmp_path) == 5123


def test_default_log_appends_and_swallows_oserror(tmp_path) -> None:
    H._default_log(tmp_path, "hello")
    assert "hello" in (tmp_path / H.UNAVAILABLE_LOG).read_text(encoding="utf-8")
    # A directory where the log file should be forces the OSError branch.
    bad_root = tmp_path / "sub"
    bad_root.mkdir()
    (bad_root / H.UNAVAILABLE_LOG).mkdir()
    H._default_log(bad_root, "swallowed")  # must not raise


# --- Default lock seams ----------------------------------------------------


def test_default_lock_acquire_contention_and_release(tmp_path) -> None:
    first = H._default_acquire_lock(tmp_path)
    assert first is not None
    assert H._default_acquire_lock(tmp_path) is None  # O_EXCL contention
    H._default_release_lock(tmp_path, first)
    again = H._default_acquire_lock(tmp_path)
    assert again is not None
    H._default_release_lock(tmp_path, again)
    assert not (tmp_path / H.LOCK_FILE).exists()


def test_default_release_lock_swallows_oserror(tmp_path) -> None:
    # Bad fd and a nonexistent path exercise both defensive except arms.
    H._default_release_lock(tmp_path, (tmp_path / "missing.lock", -1))


def test_reclaim_missing_lock_returns_false(tmp_path) -> None:
    assert H._default_reclaim_stale_lock(tmp_path) is False


def test_reclaim_malformed_lock_returns_false(tmp_path) -> None:
    (tmp_path / H.LOCK_FILE).write_text("123\n", encoding="utf-8")  # one line
    assert H._default_reclaim_stale_lock(tmp_path) is False


def test_reclaim_non_int_lock_returns_false(tmp_path) -> None:
    (tmp_path / H.LOCK_FILE).write_text("abc\n123\n", encoding="utf-8")
    assert H._default_reclaim_stale_lock(tmp_path) is False


def test_reclaim_recent_lock_not_stale(tmp_path) -> None:
    (tmp_path / H.LOCK_FILE).write_text(
        f"{os.getpid()}\n{int(time.time())}\n", encoding="utf-8"
    )
    assert H._default_reclaim_stale_lock(tmp_path) is False


def test_reclaim_stale_but_live_pid_returns_false(tmp_path) -> None:
    (tmp_path / H.LOCK_FILE).write_text(
        f"{os.getpid()}\n{int(time.time()) - 600}\n", encoding="utf-8"
    )
    assert H._default_reclaim_stale_lock(tmp_path) is False


def test_reclaim_stale_dead_pid_reclaims(tmp_path) -> None:
    (tmp_path / H.LOCK_FILE).write_text(
        f"{2**31 - 1}\n{int(time.time()) - 600}\n", encoding="utf-8"
    )
    assert H._default_reclaim_stale_lock(tmp_path) is True
    assert not (tmp_path / H.LOCK_FILE).exists()


# --- Eight shims import cleanly and declare a well-formed spec -------------


@pytest.mark.parametrize(
    ("filename", "event", "klass"),
    [
        ("pre-tool-use.py", "PreToolUse", "B"),
        ("post-tool-use.py", "PostToolUse", "B"),
        ("subagent-start.py", "SubagentStart", "B"),
        ("subagent-stop.py", "SubagentStop", "B"),
        ("stop.py", "Stop", "B"),
        ("session-start.py", "SessionStart", "A"),
        ("user-prompt-submit.py", "UserPromptSubmit", "A"),
        ("pre-compact.py", "PreCompact", "A"),
    ],
)
def test_shim_imports_and_declares_spec(filename, event, klass) -> None:
    path = _HOOKS_DIR / filename
    spec = importlib.util.spec_from_file_location(f"shim_{event}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.SPEC.name == event
    assert module.SPEC.event_class == klass
