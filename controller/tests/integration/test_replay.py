"""Integration tests: replay TC-001..TC-124 and §11.2 extension TCs.

Loads each fixture file through the integration harness and asserts that
every TCResult.matched == True.  Failures print the mismatch_reason to aid
debugging.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from helm_controller.audit.replay import replay_tc
from tests.integration.harness import replay_all

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

_FIXTURE_FILES = [
    _FIXTURES_DIR / "tc_001_to_010_happy.json",
    _FIXTURES_DIR / "tc_101_to_115_presend.json",
    _FIXTURES_DIR / "tc_116_to_120_profile4.json",
    _FIXTURES_DIR / "tc_121_to_124_lifecycle.json",
    _FIXTURES_DIR / "tc_spec_11_2_extensions.json",
]


@pytest.mark.parametrize("fixture_path", _FIXTURE_FILES, ids=lambda p: p.name)
def test_fixture_file_all_pass(fixture_path: Path) -> None:
    """Every TC in the fixture file must have TCResult.matched == True."""
    results = replay_all(fixture_path)
    assert results, f"{fixture_path.name}: fixture file is empty or failed to load"

    failures = [r for r in results if not r.matched]
    if failures:
        msgs = "\n".join(
            f"  {r.tc_id}: {r.mismatch_reason}"
            for r in failures
        )
        pytest.fail(
            f"{fixture_path.name}: {len(failures)}/{len(results)} TC(s) did not match:\n{msgs}"
        )


def test_presend_failure_without_blackboard() -> None:
    """A turn with no blackboard that fails presend reaches the presend-fail path.

    With ``blackboard_overrides`` null, the BG-gate and invariant stages are
    skipped, so a ``deliverable_content`` outbound message is caught by the
    presend stage (CHK-004) rather than INV-001 — exercising the presend
    failure branch of ``_evaluate_turn``.
    """
    tc = {
        "tc_id": "TC-PRESEND-DIRECT",
        "turns": [
            {
                "snapshot_overrides": {"outbound_message_type": "deliverable_content"},
                "blackboard_overrides": None,
            }
        ],
        "expected_verdict": "FAIL",
        "expected_failed_check": "CHK-004",
    }
    result = replay_tc(tc)
    assert result.verdict == "FAIL"
    assert result.failed_check == "CHK-004"
    assert result.matched is True
