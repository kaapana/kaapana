"""
Behavioral tests for the PostgreSQL upgrade in migration-0.6.x-0.7.x.sh: an upgrade interrupted
between its dump and the end of its restore is finished by the next run, a finished one is left
alone, and only the start of a helper pod is limited in time. No cluster and no PostgreSQL:
kubectl is a stub on PATH that runs each helper pod's script against the test's data directory,
with stand-ins for the PostgreSQL tools.

Run from anywhere:
    pytest utils/migration-chart/tests/test_migration_0_6_x_0_7_x_resume.py
"""

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "docker" / "files" / "migration-0.6.x-0.7.x.sh"

# "apply" runs the pod's script with /pv and /tmp inside the sandbox and keeps its end as the
# pod's phase. A pod named in $BROKEN_PODS fails without running. The first $RUNNING_POLLS
# questions for a phase are answered with $PHASE_MEANWHILE. Without the old admin project
# namespace the migration ends after the database upgrade.
KUBECTL = """#!/bin/bash
case "$*" in
  apply*)
    manifest=$(cat)
    name=$(sed -n 's/^metadata: {name: \\([^,]*\\),.*/\\1/p' <<<"$manifest")
    echo "$name" >> "$SANDBOX/pods"
    if [[ " $BROKEN_PODS " == *" ${name%%-*} "* ]]; then echo Failed > "$SANDBOX/phase"; exit 0; fi
    script=$(sed -n '/^    - |$/,/^    volumeMounts:/p' <<<"$manifest" | sed '1d;$d;s/^      //' |
      sed "s#/tmp/#$SANDBOX/#g;s#/pv/#$FAST_DATA_DIR/#g")
    if PATH="$SANDBOX/tools:$PATH" sh -ec "$script" > "$SANDBOX/$name.log" 2>&1
    then echo Succeeded; else echo Failed; fi > "$SANDBOX/phase"
    ;;
  "get pod "*)
    polls=$(cat "$SANDBOX/polls" 2>/dev/null || echo 0)
    echo $((polls + 1)) > "$SANDBOX/polls"
    if [[ $polls -lt ${RUNNING_POLLS:-0} ]]; then echo "$PHASE_MEANWHILE"; else cat "$SANDBOX/phase"; fi
    ;;
  "get namespace "*) exit 1 ;;
esac
"""

TOOLS = {
    "su-exec": 'shift\nexec "$@"',
    "postgres": "echo ' rolname = \"postgres\"'",
    "pg_dumpall": "echo '-- dump'",
    "initdb": 'mkdir -p "$PGDATA" && echo 18 > "$PGDATA/PG_VERSION"',
    "pg_ctl": "exit 0",
    "psql": "exit 0",
    "chown": "exit 0",
    "sleep": "exit 0",
}


class Site:
    def __init__(self, tmp_path: Path) -> None:
        self.sandbox = tmp_path / "sandbox"
        self.volume = tmp_path / "fast" / "admin-keycloak-pv-claim-pvc-1234"
        tools = self.sandbox / "tools"
        tools.mkdir(parents=True)
        for name, body in {**TOOLS, "kubectl": KUBECTL}.items():
            (tools / name).write_text(body if body.startswith("#!") else f"#!/bin/sh\n{body}\n")
            (tools / name).chmod(0o755)
        (self.volume / "data").mkdir(parents=True)
        (self.volume / "data" / "PG_VERSION").write_text("17\n")

    def migrate(self, **knobs: str) -> subprocess.CompletedProcess:
        for leftover in ("pods", "polls"):
            (self.sandbox / leftover).unlink(missing_ok=True)
        env = dict(
            os.environ, PATH=f"{self.sandbox / 'tools'}:{os.environ['PATH']}", SANDBOX=str(self.sandbox),
            STORAGE_PROVIDER="microk8s.io/hostpath", STORAGE_CLASS_WORKFLOW="wf", ADMIN_NAMESPACE="admin",
            PLATFORM_PREFIX="kaapana", MIGRATION_IMAGE="img", PG17_IMAGE="pg17", PG18_IMAGE="pg18",
            FAST_DATA_DIR=str(self.volume.parent), BROKEN_PODS="",
        )
        env.update(knobs)
        return subprocess.run(["bash", str(SCRIPT)], cwd=self.sandbox, env=env, capture_output=True, text=True)

    def pods(self) -> list[str]:
        started = self.sandbox / "pods"
        return [name.split("-")[0] for name in started.read_text().split()] if started.exists() else []

    def upgraded(self) -> bool:
        new = self.volume / "data" / "18" / "docker" / "PG_VERSION"
        return new.is_file() and new.read_text().strip() == "18"


@pytest.fixture
def site(tmp_path: Path) -> Site:
    return Site(tmp_path)


def test_an_upgrade_interrupted_in_its_restore_is_finished_by_the_next_run(site: Site):
    first = site.migrate(BROKEN_PODS="pg18restore")
    assert first.returncode != 0 and "RESTORE FAILED" in first.stdout, first.stdout + first.stderr
    # What the interruption leaves: the PG17 cluster moved away, its dump, and nothing in place.
    assert (site.volume / "data_pg17_bak" / "PG_VERSION").read_text().strip() == "17"
    assert (site.volume / "dumpall.sql").is_file() and not any((site.volume / "data").iterdir())

    second = site.migrate()
    assert second.returncode == 0, second.stdout + second.stderr
    assert site.pods() == ["pg17dump", "pg18restore"] and site.upgraded(), second.stdout
    assert "already-dumped" in (site.sandbox / "pg17dump-admin-keycloak-pv-claim.log").read_text()

    third = site.migrate()
    assert third.returncode == 0 and site.pods() == [] and site.upgraded(), third.stdout + third.stderr
    assert "No PG17 clusters found" in third.stdout


def test_a_running_dump_is_waited_for_beyond_the_start_limit(site: Site):
    result = site.migrate(RUNNING_POLLS="350", PHASE_MEANWHILE="Running")
    assert result.returncode == 0 and site.upgraded(), result.stdout + result.stderr


def test_a_pod_that_does_not_start_fails_its_database(site: Site):
    result = site.migrate(RUNNING_POLLS="350", PHASE_MEANWHILE="Pending")
    assert result.returncode != 0 and "DUMP FAILED" in result.stdout, result.stdout + result.stderr
    assert not site.upgraded()
