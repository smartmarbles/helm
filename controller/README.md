# helm-controller

Host-neutral policy boundary for the Helm orchestration runtime. The controller
sits behind Copilot agent hooks (PreToolUse, Stop, SubagentStop, …), evaluates
the per-turn runtime snapshot against the gate / invariant / lifecycle policy,
and returns an `allow | deny | ask` decision.

This package is greenfield scaffolding established in spec015 Phase 1. Most
subpackages (`contracts`, `hooks`, `store`, `policy`, `fsm`, `gates`,
`invariants`, `lifecycle`, `residual`, `audit`) are filled in by later tasks.

## Requirements

- Python **3.13+** (`requires-python = ">=3.13"`). 3.13 ships `tomllib` in the
  stdlib, so config parsing carries no extra runtime dependency. Older 3.9–3.12
  releases are not supported.

## Install (development)

```bash
cd controller
python -m pip install -e ".[dev]"
```

Dev extras: `pytest`, `pytest-cov`. Coverage is configured in
`pyproject.toml` with branch coverage on and `fail_under = 100`.

## Run

```bash
helm-controller --workspace /path/to/workspace
```

CLI arguments:

| Argument        | Default                                                      | Purpose                                                                 |
| --------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------- |
| `--workspace`   | _(required)_                                                | Workspace root the controller governs.                                 |
| `--port`        | `0` (OS-assigned, via config)                               | Bind port. Overrides config file `[server] port`.                      |
| `--config`      | package-bundled config directory                            | Resolves `agent_roles.yaml` and `tool_classes.yaml`.                   |
| `--config-file` | `<workspace>/helm-controller.toml` if present, else defaults | TOML config overriding built-in defaults.                              |

On startup the server writes its bound port to
`<workspace>/.helm-controller.port` and removes that file on clean shutdown
(server implemented in Task 3.0).

## Configuration

The controller runs entirely on built-in defaults — no config file is required.
To override settings, copy [`helm-controller.toml.example`](../helm-controller.toml.example)
(repo root) to `helm-controller.toml` in your workspace root and uncomment the
keys you want to change. That live file is environment-specific and is
`.gitignore`d; do not commit it.

Precedence: **CLI args > config file > built-in defaults.**

## Startup mechanism

> **TBD (Task 3.0 / Watch Out #20).** `server.py` must be launched before any
> hook can reach the controller. The launch pattern (VS Code task with
> `runOn: folderOpen`, auto-start from the hook wrapper, or a manual command)
> will be chosen and documented here before Phase 3 ships.
