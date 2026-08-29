#!/usr/bin/env python3
"""Shared stdlib-only resilience helper for the eight Helm hook wrappers.

Each wrapper (`pre-tool-use.py`, `stop.py`, …) is a thin shim that declares its
event name, its event *class* (A = human-conversational, B = agent-workflow-
enforcement), and its event-native ALLOW/DENY wire shapes, then calls
:func:`run`. This module houses every resilience decision so the eight shims
stay verbatim-identical except for their declared :class:`EventSpec`.

Routing happens on two orthogonal axes (spec015 Phase R2):

* **Event class** — Class A events (UserPromptSubmit, SessionStart, PreCompact)
  may NEVER produce a chat-bricking deny; the human is never gated. Class B
  events (PreToolUse, PostToolUse, SubagentStart, SubagentStop, Stop) are
  governed normally when the controller responds and yield an *actionable
  recoverable deny* when it is unavailable.
* **Availability** — *controller-responded* (any HTTP response, honored
  verbatim) vs *controller-unavailable* (transport failure, the only state
  eligible for resilience handling).

The policy matrix:

================  ====================  ===============================
                  controller-responded  controller-unavailable
================  ====================  ===============================
Class A           honor allow/ask;      PASS (never brick) + log notice
                  a deny DEGRADES to a
                  non-blocking PASS
Class B           honor verbatim        actionable deny (default) or
                                        strict deny (per config)
================  ====================  ===============================

A bounded single-flight self-heal (one detached controller start under an
``O_EXCL`` lock) runs before any Class-B deny is surfaced, so the actionable
deny triggers only on *persistent* unavailability. A human-only ``.helm-suspend``
marker file short-circuits every event to PASS before any controller contact.

Imports are restricted to the standard library. Every external side effect
(HTTP, subprocess spawn, clock, sleep, filesystem reads) is funnelled through an
injectable :class:`Deps` so the routing logic is deterministically testable.
"""

from __future__ import annotations

import http.client
import json
import os
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# --- Stable file names and wire-contract markers --------------------------

PORT_FILE = ".helm-controller.port"
SUSPEND_FILE = ".helm-suspend"
LOCK_FILE = ".helm-controller.lock"
UNAVAILABLE_LOG = ".helm-controller-unavailable.log"
CONFIG_FILE = "helm-controller.toml"

# Load-bearing wire markers ARTHUR keys on — exact, tested, never re-spelled.
MARKER_UNAVAILABLE = "[HELM-CONTROLLER-UNAVAILABLE]"
MARKER_SUSPENDED = "[HELM-ENFORCEMENT-SUSPENDED]"
MARKER_NOTICE = "[HELM-CONTROLLER-NOTICE]"

POST_TIMEOUT = 10
STALE_LOCK_SECONDS = 30


# --- Configuration --------------------------------------------------------


@dataclass(frozen=True)
class ResilienceConfig:
    """The `[resilience]` knobs read from `helm-controller.toml`.

    Defaults implement the security philosophy: the human is never bricked, and
    a Class-B action against an unavailable controller yields an actionable deny
    (never a silent allow). Every malformed/absent config collapses to these.
    """

    class_b_unavailable: str = "actionable_deny"  # | "strict_deny"
    auto_start: bool = True
    heal_budget_seconds: float = 6.0
    poll_interval_seconds: float = 0.25


# --- Event declaration (supplied by each shim) ----------------------------


@dataclass(frozen=True)
class EventSpec:
    """Per-event wire contract declared by a wrapper shim.

    `deny_shape` selects the event-native DENY/ALLOW envelope:

    * ``"permission"`` — PreToolUse: nested ``hookSpecificOutput`` with
      ``permissionDecision`` + ``permissionDecisionReason``.
    * ``"block"`` — PostToolUse/Stop/SubagentStop: ``{"decision":"block", …}``.
    * ``"common"`` — common-output events: ``{"continue":false, "stopReason":…}``.
    """

    name: str
    event_class: str  # "A" | "B"
    allow: dict[str, Any]
    deny_shape: str  # "permission" | "block" | "common"


# --- Injectable dependency holder -----------------------------------------


@dataclass(frozen=True)
class Deps:
    """All external side effects, injectable for deterministic testing."""

    read_config: Callable[[Path], ResilienceConfig]
    suspend_exists: Callable[[Path], bool]
    read_port: Callable[[Path], int | None]
    post: Callable[[Path, int, str], str | None]
    now: Callable[[], float]
    sleep: Callable[[float], None]
    spawn: Callable[[Path], None]
    acquire_lock: Callable[[Path], object | None]
    release_lock: Callable[[Path, object], None]
    reclaim_stale_lock: Callable[[Path], bool]
    log: Callable[[Path, str], None]


# --- Wire-shape builders --------------------------------------------------


def _build_deny(spec: EventSpec, reason: str) -> dict[str, Any]:
    if spec.deny_shape == "permission":
        return {
            "hookSpecificOutput": {
                "hookEventName": spec.name,
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    if spec.deny_shape == "block":
        return {"decision": "block", "reason": reason}
    return {"continue": False, "stopReason": reason}


def _build_pass(spec: EventSpec, notice: str | None = None) -> dict[str, Any]:
    """Event-native ALLOW/proceed. A notice is embedded in-band only where a
    safe native reason field exists (PreToolUse); otherwise it is log-only."""
    out: dict[str, Any] = dict(spec.allow)
    if notice is not None and spec.deny_shape == "permission":
        hso = dict(out["hookSpecificOutput"])
        hso["permissionDecisionReason"] = notice
        out["hookSpecificOutput"] = hso
    return out


# --- Reason / notice text -------------------------------------------------


def _actionable_reason(event: str, heal_attempted: bool) -> str:
    if heal_attempted:
        guidance = (
            "The orchestration controller appears to be unavailable. I attempted "
            "to start it automatically but it did not come up within the time "
            "budget. Would you like me to try starting it again?"
        )
    else:
        guidance = (
            "The orchestration controller appears to be unavailable and automatic "
            "start is disabled. Would you like me to start it?"
        )
    trailer = (
        f" | action=offer-start | event={event} "
        f"| heal_attempted={str(heal_attempted).lower()}"
    )
    return f"{MARKER_UNAVAILABLE} {guidance}{trailer}"


def _strict_reason(event: str) -> str:
    return (
        "The orchestration controller is unavailable; this agent action was "
        f"denied. (event={event})"
    )


def _suspend_notice(event: str) -> str:
    return (
        f"{MARKER_SUSPENDED} Workflow enforcement is suspended via the "
        f".helm-suspend marker; event {event} passed without controller contact. "
        "Delete .helm-suspend to resume enforcement."
    )


def _degrade_notice(event: str) -> str:
    return (
        f"{MARKER_NOTICE} Controller returned a blocking decision on human-"
        f"conversational event {event}; degraded to a non-blocking pass "
        "(the human is never gated)."
    )


def _classa_unavailable_notice(event: str) -> str:
    return (
        f"{MARKER_NOTICE} Controller unavailable on human-conversational event "
        f"{event}; passed without gating the human."
    )


# --- Response classification ----------------------------------------------


def _response_is_deny(body: str) -> bool:
    """True if a controller response carries a blocking decision in any
    event-native shape. Used to DEGRADE a Class-A deny to a pass."""
    try:
        obj = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return False
    if not isinstance(obj, dict):
        return False
    if obj.get("continue") is False:
        return True
    if obj.get("decision") == "block":
        return True
    hso = obj.get("hookSpecificOutput")
    if isinstance(hso, dict) and hso.get("permissionDecision") == "deny":
        return True
    return False


# --- Routing core ---------------------------------------------------------


def _try_contact(root: Path, payload: str, deps: Deps) -> str | None:
    port = deps.read_port(root)
    if port is None:
        return None
    return deps.post(root, port, payload)


def _poll_for_bind(
    root: Path, config: ResilienceConfig, deps: Deps, deadline: float
) -> bool:
    while deps.now() < deadline:
        if deps.read_port(root) is not None:
            return True
        deps.sleep(config.poll_interval_seconds)
    return False


def _self_heal(root: Path, config: ResilienceConfig, deps: Deps) -> bool:
    """Bounded single-flight detached start. Returns True if a port file
    appears within the heal budget (the caller then retries the POST once)."""
    deadline = deps.now() + config.heal_budget_seconds
    token = deps.acquire_lock(root)
    if token is None and deps.reclaim_stale_lock(root):
        token = deps.acquire_lock(root)
    if token is None:
        # Another wrapper holds a live lock — poll for its spawn, never spawn.
        return _poll_for_bind(root, config, deps, deadline)
    try:
        deps.spawn(root)
        return _poll_for_bind(root, config, deps, deadline)
    finally:
        deps.release_lock(root, token)


def _honor(spec: EventSpec, body: str, root: Path, deps: Deps) -> str:
    if spec.event_class == "B":
        return body  # agent-workflow decision honored verbatim
    # Class A: a controller deny must DEGRADE to a non-blocking pass.
    if _response_is_deny(body):
        notice = _degrade_notice(spec.name)
        deps.log(root, notice)
        return json.dumps(_build_pass(spec, notice))
    return body


def _unavailable(
    spec: EventSpec,
    config: ResilienceConfig,
    root: Path,
    deps: Deps,
    heal_attempted: bool,
) -> str:
    if spec.event_class == "A":
        notice = _classa_unavailable_notice(spec.name)
        deps.log(root, notice)
        return json.dumps(_build_pass(spec, notice))
    if config.class_b_unavailable == "strict_deny":
        reason = _strict_reason(spec.name)
    else:
        reason = _actionable_reason(spec.name, heal_attempted)
    deps.log(
        root,
        f"unavailable-deny event={spec.name} "
        f"mode={config.class_b_unavailable} "
        f"heal_attempted={str(heal_attempted).lower()}: {reason}",
    )
    return json.dumps(_build_deny(spec, reason))


def _route(
    spec: EventSpec, payload: str, root: Path, config: ResilienceConfig, deps: Deps
) -> str:
    body = _try_contact(root, payload, deps)
    if body is not None:
        return _honor(spec, body, root, deps)
    if config.auto_start and _self_heal(root, config, deps):
        body = _try_contact(root, payload, deps)
        if body is not None:
            return _honor(spec, body, root, deps)
    return _unavailable(
        spec, config, root, deps, heal_attempted=config.auto_start
    )


def _dispatch(spec: EventSpec, deps: Deps, stdin: Any) -> str:
    root = _workspace_root()
    payload = stdin.read().decode("utf-8")
    config = deps.read_config(root)
    if deps.suspend_exists(root):
        notice = _suspend_notice(spec.name)
        deps.log(root, notice)
        return json.dumps(_build_pass(spec, notice))
    return _route(spec, payload, root, config, deps)


def _safe_fallback(spec: EventSpec) -> str:
    """Last-resort output if an unexpected error occurs. Class A passes (never
    brick the human); Class B denies (never a silent allow)."""
    if spec.event_class == "A":
        return json.dumps(_build_pass(spec))
    return json.dumps(_build_deny(spec, _strict_reason(spec.name)))


def run(
    spec: EventSpec,
    deps: Deps | None = None,
    stdin: Any = None,
    stdout: Any = None,
) -> int:
    """Wrapper entry point. Always exits 0 with an event-native JSON decision —
    never a traceback (a traceback could brick the human)."""
    if deps is None:
        deps = default_deps()
    if stdin is None:
        stdin = sys.stdin.buffer
    if stdout is None:
        stdout = sys.stdout
    try:
        out = _dispatch(spec, deps, stdin)
    except Exception:  # noqa: BLE001 — last-resort guard; never traceback to VS Code
        out = _safe_fallback(spec)
    stdout.write(out)
    return 0


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


# --- Default (production) dependency implementations ----------------------


def _default_read_config(root: Path) -> ResilienceConfig:
    path = root / CONFIG_FILE
    try:
        with open(path, "rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return ResilienceConfig()
    section = data.get("resilience")
    if not isinstance(section, dict):
        return ResilienceConfig()
    mode = section.get("class_b_unavailable")
    if mode not in ("actionable_deny", "strict_deny"):
        mode = ResilienceConfig.class_b_unavailable
    auto = section.get("auto_start")
    if not isinstance(auto, bool):
        auto = ResilienceConfig.auto_start
    budget = _positive_number(
        section.get("heal_budget_seconds"), ResilienceConfig.heal_budget_seconds
    )
    interval = _positive_number(
        section.get("poll_interval_seconds"),
        ResilienceConfig.poll_interval_seconds,
    )
    return ResilienceConfig(mode, auto, budget, interval)


def _positive_number(value: Any, default: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    if value <= 0:
        return default
    return float(value)


def _default_suspend_exists(root: Path) -> bool:
    return (root / SUSPEND_FILE).exists()


def _default_read_port(root: Path) -> int | None:
    try:
        return int((root / PORT_FILE).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _default_log(root: Path, message: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {message}\n"
    try:
        with open(root / UNAVAILABLE_LOG, "a", encoding="utf-8") as handle:
            handle.write(line)
    except OSError:
        pass


def _default_acquire_lock(root: Path) -> object | None:
    path = root / LOCK_FILE
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except OSError:
        return None
    payload = f"{os.getpid()}\n{int(time.time())}\n".encode("utf-8")
    try:
        os.write(fd, payload)
    except OSError:  # pragma: no cover - defensive write guard
        pass
    return (path, fd)


def _default_release_lock(root: Path, token: object) -> None:
    path, fd = token  # type: ignore[misc]
    try:
        os.close(fd)
    except OSError:
        pass
    try:
        os.unlink(str(path))
    except OSError:
        pass


def _default_reclaim_stale_lock(root: Path) -> bool:
    """Reclaim a lock only when its owning pid is provably dead AND it is older
    than the staleness threshold — the single deletion a wrapper may perform."""
    path = root / LOCK_FILE
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        pid = int(lines[0])
        created = int(lines[1])
    except (OSError, ValueError, IndexError):
        return False
    if time.time() - created < STALE_LOCK_SECONDS:
        return False
    if _pid_alive(pid):
        return False
    try:
        path.unlink()
        return True
    except OSError:  # pragma: no cover - defensive unlink guard
        return False


def _pid_alive(pid: int) -> bool:  # pragma: no cover - OS/process probe
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        process_query = 0x1000  # PROCESS_QUERY_LIMITED_INFORMATION
        still_active = 259
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(process_query, False, pid)
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel32.CloseHandle(handle)
        return bool(ok) and code.value == still_active
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _default_post(root: Path, port: int, payload: str) -> str | None:  # pragma: no cover - real socket I/O
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=POST_TIMEOUT)
    try:
        conn.request(
            "POST",
            "/hook",
            body=payload.encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        return response.read().decode("utf-8")
    except OSError:
        return None
    finally:
        conn.close()


def _default_spawn(root: Path) -> None:  # pragma: no cover - real subprocess spawn
    log_path = root / UNAVAILABLE_LOG
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root / "controller" / "src")
    if os.name == "nt":
        cmd = ["py", "-3", "-m", "helm_controller", "--workspace", str(root)]
        creationflags = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
        new_session = False
    else:
        cmd = ["python3", "-m", "helm_controller", "--workspace", str(root)]
        creationflags = 0
        new_session = True
    handle = open(log_path, "ab")
    try:
        subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=handle,
            close_fds=True,
            cwd=str(root),
            env=env,
            creationflags=creationflags,
            start_new_session=new_session,
        )
    finally:
        handle.close()


def default_deps() -> Deps:
    return Deps(
        read_config=_default_read_config,
        suspend_exists=_default_suspend_exists,
        read_port=_default_read_port,
        post=_default_post,
        now=time.monotonic,
        sleep=time.sleep,
        spawn=_default_spawn,
        acquire_lock=_default_acquire_lock,
        release_lock=_default_release_lock,
        reclaim_stale_lock=_default_reclaim_stale_lock,
        log=_default_log,
    )
