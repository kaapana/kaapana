"""Unit tests for the run_sync_round_quietly() helper in start.sh.

Pytest port of test_start.sh. Extracts the function straight out of start.sh
(rather than keeping a copy here) so these tests always exercise the current
code, not a stale fork of it. Each test runs the function in a real bash
subprocess under `set -eu`, matching production conditions exactly (this
matters: the bug these tests guard against only shows up under `set -e`).
"""

import subprocess
from pathlib import Path

import pytest

START_SH = Path(__file__).parent / "start.sh"

FAKE_COMMANDS = """
fake_fail() { echo "some transient rclone error"; return 1; }
fake_fail_17() { echo "boom"; return 17; }
fake_noop() { echo "There was nothing to transfer"; return 0; }
fake_changes() { echo "Transferred: 3 files"; return 0; }
"""


def run_bash(script: str) -> subprocess.CompletedProcess:
    """Run a bash snippet with run_sync_round_quietly() and the fakes in scope."""
    preamble = (
        "set -eu\n"
        f"extracted=\"$(awk '/^run_sync_round_quietly\\(\\) \\{{/,/^\\}}/' "
        f"{START_SH})\"\n"
        'eval "$extracted"\n' + FAKE_COMMANDS
    )
    return subprocess.run(
        ["bash", "-c", preamble + script],
        capture_output=True,
        text=True,
    )


def test_bare_call_in_loop_survives_repeated_failures():
    """FETCH/PUSH shape: a bare call in a `while` loop must not crash under set -e."""
    result = run_bash(
        """
        i=0
        while [[ $i -lt 3 ]]; do
            i=$((i + 1))
            if ! run_sync_round_quietly "There was nothing to transfer" fake_fail >/dev/null; then
                :
            fi
        done
        echo "$i"
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "3"


def test_or_result_call_survives_and_reports_failure():
    """SYNC branch shape: `cmd || RESULT=$?` must not crash and must report failure."""
    result = run_bash(
        """
        RESULT=0
        run_sync_round_quietly "No changes found" fake_fail >/dev/null || RESULT=$?
        echo "$RESULT"
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "1"


def test_exact_exit_code_is_preserved_not_just_nonzero():
    """Regression guard: an earlier fix attempt used

    `if ! cmd; then result=$?; fi`, which looks equivalent to the
    `cmd && result=0 || result=$?` idiom but isn't -- `!` inverts $? along
    with the branch taken, so `result` was always captured as 0 even on
    failure. Asserting a *specific* nonzero code (17, not just "nonzero")
    is what catches that class of bug.
    """
    result = run_bash(
        """
        RESULT=0
        run_sync_round_quietly "No changes found" fake_fail_17 >/dev/null || RESULT=$?
        echo "$RESULT"
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "17"


def test_no_op_pattern_match_suppresses_output_and_returns_success():
    result = run_bash(
        """
        RESULT=0
        output="$(run_sync_round_quietly "There was nothing to transfer" fake_noop)" || RESULT=$?
        echo "RESULT=$RESULT"
        echo "OUTPUT=[$output]"
        """
    )
    assert result.returncode == 0, result.stderr
    assert "RESULT=0" in result.stdout
    assert "OUTPUT=[]" in result.stdout


def test_real_changes_are_still_logged_not_swallowed():
    result = run_bash(
        """
        run_sync_round_quietly "There was nothing to transfer" fake_changes
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Transferred: 3 files"


@pytest.mark.parametrize("exit_code", [0, 1, 2, 17, 42])
def test_exit_code_matrix(exit_code):
    """Sweep several distinct nonzero codes to make sure none collapse to 0/1."""
    result = run_bash(
        f"""
        fake() {{ return {exit_code}; }}
        RESULT=0
        run_sync_round_quietly "No changes found" fake >/dev/null || RESULT=$?
        echo "$RESULT"
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(exit_code)
