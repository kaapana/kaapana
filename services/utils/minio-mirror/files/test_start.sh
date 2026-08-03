#!/bin/bash
# Unit tests for the run_sync_round_quietly() helper in start.sh.
#
# Extracts the function straight out of start.sh (rather than keeping a copy
# here) so these tests always exercise the current code, not a stale fork of
# it. Run directly: ./test_start.sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
START_SH="$SCRIPT_DIR/start.sh"

# shellcheck disable=SC2317
extracted="$(awk '/^run_sync_round_quietly\(\) \{/,/^\}/' "$START_SH")"
eval "$extracted"

failures=0

assert_eq() {
    local expected="$1" actual="$2" desc="$3"
    if [[ "$expected" == "$actual" ]]; then
        echo "PASS: $desc"
    else
        echo "FAIL: $desc (expected '$expected', got '$actual')"
        failures=$((failures + 1))
    fi
}

fake_fail() { echo "some transient rclone error"; return 1; }
fake_fail_17() { echo "boom"; return 17; }
fake_noop() { echo "There was nothing to transfer"; return 0; }
fake_changes() { echo "Transferred: 3 files"; return 0; }

echo "=== bare call in a while loop (FETCH/PUSH shape) must not crash the script under set -e ==="
i=0
while [[ $i -lt 3 ]]; do
    i=$((i + 1))
    if ! run_sync_round_quietly "There was nothing to transfer" fake_fail >/dev/null; then
        :
    fi
done
assert_eq 3 "$i" "loop survives 3 consecutive failures without errexit killing the script"

echo
echo "=== '|| RESULT=\$?' call (SYNC branch shape) must not crash and must report failure ==="
RESULT=0
run_sync_round_quietly "No changes found" fake_fail >/dev/null || RESULT=$?
assert_eq 1 "$RESULT" "RESULT reflects fake_fail's nonzero exit"

echo
echo "=== exact exit code must survive, not just nonzero-ness ==="
# This is the regression this suite exists to catch: an earlier attempt used
# `if ! cmd; then result=$?; fi`, which looks equivalent but isn't --
# `!` inverts $? along with the branch taken, so result was always 0 even
# on failure. Asserting a *specific* nonzero code (17, not just "nonzero")
# is what catches that.
RESULT=0
run_sync_round_quietly "No changes found" fake_fail_17 >/dev/null || RESULT=$?
assert_eq 17 "$RESULT" "specific exit code (17) is preserved, not collapsed to 0 or 1"

echo
echo "=== no-op pattern match suppresses output and returns success ==="
RESULT=0
output="$(run_sync_round_quietly "There was nothing to transfer" fake_noop)" || RESULT=$?
assert_eq 0 "$RESULT" "no-op round returns success"
assert_eq "" "$output" "no-op round produces no output (quiet)"

echo
echo "=== real changes are still logged, not swallowed ==="
output="$(run_sync_round_quietly "There was nothing to transfer" fake_changes)"
assert_eq "Transferred: 3 files" "$output" "non-no-op output is surfaced"

echo
if [[ $failures -eq 0 ]]; then
    echo "All tests passed."
    exit 0
else
    echo "$failures test(s) failed."
    exit 1
fi
