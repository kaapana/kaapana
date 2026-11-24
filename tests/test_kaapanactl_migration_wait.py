import os
import re
import subprocess
import tarfile
from pathlib import Path

KAAPANACTL = Path(__file__).resolve().parents[1] / "kaapanactl.sh"

# The job's pod starts after $START polls and ends after $END; kaapanactl asks once per poll
# whether a pod of the job is running.
KUBECTL = """#!/bin/bash
polls=$(cat "$POLLS" 2>/dev/null || echo 0)
case "$*" in
  *phase=Running*) echo $((polls + 1)) > "$POLLS"; [[ $polls -ge $START && $polls -lt $END ]] && echo pod/migration-x ;;
  *status.succeeded*) [[ $polls -ge $END ]] && echo 1 ;;
esac
exit 0
"""


def wait_for_migration(tmp_path, start, end):
    # kaapanactl.sh runs main on load, so only the functions under test are sourced.
    functions = re.findall(
        r"^function (?:run_migration_chart|find_subchart)\(\) \{.*?^\}", KAAPANACTL.read_text(), re.S | re.M
    )
    assert any("run_migration_chart" in f for f in functions), "run_migration_chart missing from kaapanactl.sh"
    for name, body in {"microk8s.kubectl": KUBECTL, "helm": "#!/bin/bash\n", "sleep": "#!/bin/bash\n"}.items():
        (tmp_path / name).write_text(body)
        (tmp_path / name).chmod(0o755)
    chart = tmp_path / "platform" / "charts" / "migration-chart"
    chart.mkdir(parents=True)
    (chart / "Chart.yaml").write_text("name: migration-chart\n")
    with tarfile.open(tmp_path / "platform.tgz", "w:gz") as package:
        package.add(tmp_path / "platform", arcname="platform")
    env = {
        **os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "TMPDIR": str(tmp_path),
        "POLLS": str(tmp_path / "polls"), "START": str(start), "END": str(end),
        "CHART_PATH": str(tmp_path / "platform.tgz"), "PLATFORM_NAME": "platform",
        "HELM_EXECUTABLE": str(tmp_path / "helm"), "KUBECTL_EXECUTABLE": str(tmp_path / "microk8s.kubectl"),
    }
    result = subprocess.run(
        ["bash", "-c", "\n".join(functions) + "\nrun_migration_chart 0.6.1 0.7.0"],
        env=env, capture_output=True, text=True,
    )
    return result, int((tmp_path / "polls").read_text())


def test_a_running_migration_is_waited_for_beyond_the_start_limit(tmp_path):
    result, polls = wait_for_migration(tmp_path, start=10, end=200)  # runs 190 polls of 5 s
    assert result.returncode == 0 and "completed successfully" in result.stdout, result.stdout + result.stderr
    assert polls == 200


def test_a_migration_that_does_not_start_ends_the_wait(tmp_path):
    result, polls = wait_for_migration(tmp_path, start=10**6, end=10**6)
    assert result.returncode == 1 and "did not start within 600s" in result.stdout, result.stdout + result.stderr
    assert polls == 120
