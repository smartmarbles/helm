"""Integration test harness — loads TC fixture files and replays all TCs.

Thin file-I/O wrapper around audit.replay.replay_tc.  The replay logic lives
in the source tree (helm_controller.audit.replay) so it is importable from
both here and from audit.hk_lens.hk_008.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from helm_controller.audit.replay import TCResult, replay_tc


def load_fixtures(path: Path) -> list[dict[str, Any]]:
    """Load a TC fixture JSON file and return the list of TC dicts."""
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, list):
        return data
    return data.get("test_cases", [])


def replay_all(path: Path) -> list[TCResult]:
    """Load and replay every TC in a fixture file; return all results."""
    return [replay_tc(tc) for tc in load_fixtures(path)]
