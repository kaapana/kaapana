"""What the pipeline is made of, per set of inputs.

Catches the class of bug that only shows up in a real pipeline: a `needs:` on a
job nobody defines, a readiness gate that stops covering a case, an artifact a
later job expects and no job writes.
"""

import re

import pytest
from conftest import DEPLOY_INPUTS, FQDN, jobs, merged_config


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


@pytest.mark.parametrize(
    "toggle,job",
    [
        ("exec_deploy", "platform_deployment"),
        ("exec_build", "build_packages"),
        ("exec_unit_tests", "unit_tests"),
        ("exec_lint", "lint"),
    ],
)
def test_toggle_off_never_runs_the_job(toggle, job):
    """Every rule that depends on inputs alone must be false. Rules carrying a
    variable (the release-tag rule below) are GitLab's to evaluate."""
    config = merged_config(inputs=(f"{toggle}=false",))
    conditions = [c for c in rule_ifs(jobs(config)[job]) if c]
    assert all(statically_false(c) or "$" in c for c in conditions), conditions


def test_release_tag_builds_even_with_build_off():
    """A release tag publishes to the release registry, so build_packages runs
    whatever exec_build says."""
    config = merged_config(inputs=("exec_build=false",))
    tag_rules = [rule for rule in jobs(config)["build_packages"]["rules"] if "CI_COMMIT_TAG" in rule.get("if", "")]
    assert tag_rules, "build_packages lost its release-tag rule"
    assert tag_rules[0]["variables"]["REGISTRY_URL"] == "$RELEASE_REGISTRY_URL"


def test_integration_tests_need_a_deployment():
    """Without a deployment there is no target to test against."""
    config = merged_config(inputs=("exec_integration_tests=true", "exec_deploy=false"))
    for name in ("scan_ports", "first_login", "send_data"):
        conditions = [c for c in rule_ifs(jobs(config)[name]) if c]
        assert all(statically_false(c) for c in conditions), name


def test_external_target_is_never_destroyed():
    config = merged_config(inputs=("exec_deploy=true",), variables=(FQDN,))
    first_rule = jobs(config)["destroy_deployment"]["rules"][0]
    assert first_rule["when"] == "never"
    assert "DEPLOYMENT_INSTANCE_FQDN" in first_rule["if"]
