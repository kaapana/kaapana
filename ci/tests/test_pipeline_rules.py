"""What the pipeline is made of, per set of inputs.

Catches the class of bug that only shows up in a real pipeline: a `needs:` on a
job nobody defines, a readiness gate that stops covering a case, an artifact a
later job expects and no job writes.
"""

import re
from pathlib import Path

import pytest
import yaml
from conftest import DEPLOY_INPUTS, FQDN, jobs, merged_config

CI_DIR = Path(__file__).resolve().parents[1]


def rule_ifs(job):
    return [rule.get("if", "") for rule in job.get("rules", [])]


def statically_false(condition):
    """True when the input half of a resolved rule can never match.

    gitlab-ci-local substitutes the inputs, so a condition reads e.g.
    '"true" == "true" && "false" != "true" && $DEPLOYMENT_INSTANCE_FQDN != ""'.
    Clauses that still carry a variable are left to GitLab; the literal ones
    decide here.
    """
    for clause in condition.split("&&"):
        match = re.fullmatch(r'\s*"([^"]*)"\s*(==|!=)\s*"([^"]*)"\s*', clause)
        if not match:
            continue
        left, operator, right = match.groups()
        if (operator == "==" and left != right) or (operator == "!=" and left == right):
            return True
    return False


def test_every_needed_job_exists(default_config):
    """A `needs:` naming a job that does not exist is silently accepted by
    GitLab when it is optional — the dependency simply never applies."""
    defined = set(jobs(default_config))
    missing = {}
    for name, body in jobs(default_config).items():
        for need in body.get("needs", []):
            needed = need["job"] if isinstance(need, dict) else need
            if needed not in defined:
                missing.setdefault(name, []).append(needed)
    assert not missing, f"needs pointing at jobs that do not exist: {missing}"


def test_preflight_target_waits_for_preflight_variables(default_config):
    """Otherwise it SSHes into a target whose FQDN was already rejected."""
    needs = [n["job"] for n in jobs(default_config)["preflight_target"]["needs"]]
    assert "preflight_variables" in needs


@pytest.mark.parametrize(
    "server_installation",
    ["false", "true"],  # with the install it is advisory, but it runs
)
def test_a_readiness_job_guards_every_given_target(server_installation):
    """A fresh VM is checked by server_installation itself; a target given by
    FQDN is only ever checked by preflight_target."""
    config = merged_config(
        inputs=DEPLOY_INPUTS + (f"exec_server_installation={server_installation}",),
        variables=(FQDN,),
    )
    condition = rule_ifs(jobs(config)["preflight_target"])[0]
    assert not statically_false(condition), condition
    # The FQDN half is evaluated by GitLab at pipeline creation.
    assert "DEPLOYMENT_INSTANCE_FQDN" in condition, condition


def test_preflight_target_uses_the_configured_target_and_credentials():
    """Target, SSH user and key all come from the DEPLOYMENT_INSTANCE_*
    variables; nothing about the check is hardcoded to one host."""
    config = merged_config(inputs=DEPLOY_INPUTS, variables=(FQDN,))
    job = jobs(config)["preflight_target"]
    assert job["variables"]["VM_FQDN"] == "$DEPLOYMENT_INSTANCE_FQDN"
    assert job["variables"]["VM_USER"] == "$DEPLOYMENT_INSTANCE_USER"
    script = "\n".join(job["script"])
    assert '-u "$VM_USER"' in script
    assert '--private-key "$DEPLOYMENT_INSTANCE_SSH_KEY"' in script
    assert '-i "$VM_FQDN,"' in script
    # chmod 600 first: ssh refuses a key the runner checked out world-readable.
    assert 'chmod 600 "$DEPLOYMENT_INSTANCE_SSH_KEY"' in "\n".join(job["before_script"])


@pytest.mark.parametrize("redeploy", ["true", "false"])
def test_both_mode_knobs_reach_the_job(redeploy):
    """The two inputs that decide what is fatal (see test_readiness_modes)."""
    config = merged_config(
        inputs=DEPLOY_INPUTS + (f"exec_redeploy={redeploy}", "exec_server_installation=false"),
        variables=(FQDN,),
    )
    variables = jobs(config)["preflight_target"]["variables"]
    assert variables["CI_EXEC_REDEPLOY"] == redeploy
    assert variables["CI_EXEC_SERVER_INSTALLATION"] == "false"


def test_readiness_job_publishes_its_table():
    """The table is the whole point of the job; it must survive the run."""
    inputs = DEPLOY_INPUTS + ("exec_server_installation=false",)
    artifacts = jobs(merged_config(inputs=inputs, variables=(FQDN,)))["preflight_target"]["artifacts"]
    assert artifacts["when"] == "always"
    assert any("target_readiness.log" in path for path in artifacts["paths"])
    assert any("target_readiness.json" in path for path in artifacts["paths"])


TOGGLES = (
    "exec_unit_tests",
    "exec_lint",
    "exec_build",
    "exec_deploy",
    "exec_server_installation",
    "exec_integration_tests",
    "exec_security_scan",
    "exec_ci_image_rebuild",
    "exec_vm_sweep",
)

TOGGLED_JOBS = [
    ("exec_unit_tests", "unit_tests"),
    ("exec_unit_tests", "ci_config_tests"),
    ("exec_unit_tests", "build_documentation"),
    ("exec_lint", "lint"),
    ("exec_build", "build_packages"),
    ("exec_deploy", "prepare_deployment"),
    ("exec_deploy", "platform_deployment"),
    ("exec_deploy", "destroy_deployment"),
    ("exec_server_installation", "server_installation"),
    ("exec_integration_tests", "setup_integration_tests"),
    ("exec_integration_tests", "scan_ports"),
    ("exec_integration_tests", "first_login"),
    ("exec_integration_tests", "install_extensions"),
    ("exec_integration_tests", "send_data"),
    ("exec_integration_tests", "run_workflows"),
    ("exec_integration_tests", "playwright_ui_tests"),
    ("exec_security_scan", "security_scan"),
    ("exec_ci_image_rebuild", "build_ci_image"),
    ("exec_vm_sweep", "sweep_deployment_vms"),
]


@pytest.mark.parametrize("toggle,job", TOGGLED_JOBS)
def test_toggle_on_always_runs_the_job(toggle, job):
    """Every other toggle off: one rule decided by the inputs alone must match,
    so each stage runs without the others."""
    inputs = tuple(f"{other}={str(other == toggle).lower()}" for other in TOGGLES)
    conditions = [c for c in rule_ifs(jobs(merged_config(inputs=inputs))[job]) if c]
    assert any("$" not in c and not statically_false(c) for c in conditions), conditions


@pytest.mark.parametrize("toggle,job", TOGGLED_JOBS)
def test_toggle_off_never_runs_the_job(toggle, job):
    """Every rule that depends on inputs alone must be false. Rules carrying a
    variable (the release-tag rule below) are GitLab's to evaluate."""
    config = merged_config(inputs=(f"{toggle}=false",))
    conditions = [c for c in rule_ifs(jobs(config)[job]) if c]
    assert all(statically_false(c) or "$" in c for c in conditions), conditions


def test_failure_notification_fires_on_any_failed_job(default_config):
    """if_ci_failing runs on develop if any job fails"""
    config = jobs(default_config)
    job = config["if_ci_failing"]
    assert "needs" not in job, "needs: would make if_ci_failing skip itself instead of reporting the failure"
    stages = default_config["stages"]
    for name in job["dependencies"]:
        assert name in config, f"dependencies names a job that does not exist: {name}"
        assert stages.index(config[name]["stage"]) < stages.index(job["stage"]), name


def test_external_target_is_never_destroyed():
    config = merged_config(inputs=("exec_deploy=true",), variables=(FQDN,))
    first_rule = jobs(config)["destroy_deployment"]["rules"][0]
    assert first_rule["when"] == "never"
    assert "DEPLOYMENT_INSTANCE_FQDN" in first_rule["if"]


def test_preflight_variables_checks_the_registry_scope_the_build_uses(default_config):
    all_jobs = jobs(default_config)
    assert all_jobs["build_packages"]["environment"]["name"] == "$REGISTRY_ENV"
    environment = all_jobs["preflight_variables"]["environment"]
    assert environment["name"] == "$REGISTRY_ENV"
    assert environment["action"] == "access"


def test_the_admin_chart_and_namespace_come_from_the_variables():
    files = [*(CI_DIR / "pipeline").glob("*.yml"), *(CI_DIR / "ci-code").rglob("*.yaml")]
    offenders = [str(f.relative_to(CI_DIR)) for f in files if "kaapana-admin-chart" in f.read_text()]
    assert not offenders, f"literal chart name instead of DEPLOYMENT_INSTANCE_ADMIN_CHART in {offenders}"

    setup = CI_DIR / "ci-code" / "integration_tests" / "remote_execution" / "setup_integration_tests.yaml"
    play = yaml.safe_load(setup.read_text())[0]
    assert "DEPLOYMENT_INSTANCE_ADMIN_CHART" in play["vars"]["admin_chart"]
    assert "DEPLOYMENT_INSTANCE_HELM_NAMESPACE" in play["vars"]["helm_namespace"]
    lookup = next(task for task in play["tasks"] if "ansible.builtin.shell" in task)["ansible.builtin.shell"]
    assert "-n {{ helm_namespace | quote }} get values {{ admin_chart | quote }}" in lookup


def test_build_does_not_lint_charts(default_config):
    """Charts are linted by lint: [helm] in the tests stage; the build must not repeat it."""
    script = "\n".join(jobs(default_config)["build_packages"]["script"])
    assert "--no-linting" in script


def test_every_linter_has_its_commands(default_config):
    """A LINTER added to the lint matrix without a case in the script would fail every pipeline."""
    job = jobs(default_config)["lint"]
    linters = [linter for entry in job["parallel"]["matrix"] for linter in entry["LINTER"]]
    script = "\n".join(job["script"])
    assert linters
    for linter in linters:
        assert f"{linter})" in script, linter
    assert job["artifacts"]["reports"]["codequality"] == "gl-code-quality-report.json"
