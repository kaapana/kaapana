"""What preflight_variables accepts and rejects.

The script under test is the one from the merged config, so these are the
checks that actually ship. Each case sets an environment and asserts the exit
code and the message a developer would read in the job log.
"""

import subprocess

import pytest
from conftest import DEPLOY_INPUTS, jobs, merged_config


def write_script(config, directory):
    """The job's script, preceded by its `variables:` as GitLab exports them."""
    job = jobs(config)["preflight_variables"]
    exports = [f'export {name}="{value}"' for name, value in job.get("variables", {}).items()]
    path = directory / "check_variables.sh"
    path.write_text("\n".join(exports + job["script"]) + "\n")
    return path


@pytest.fixture(scope="module")
def script(tmp_path_factory):
    return write_script(merged_config(inputs=DEPLOY_INPUTS), tmp_path_factory.mktemp("preflight"))


@pytest.fixture
def env(tmp_path):
    """A run that must pass: every variable a deployment needs, all valid."""
    key = tmp_path / "ssh_key"
    key.write_text("not a real key\n")
    return {
        "PATH": "/usr/bin:/bin",
        "CI_REGISTRY_URL": "reg.example/kaapana",
        "CI_IMAGES_TAG": "v7",
        "CI_REGISTRY_USER": "ci",
        "CI_REGISTRY_TOKEN": "token",
        "DOCKER_AUTH_CONFIG": '{"auths":{"reg.example":{}}}',
        "REGISTRY_URL": "reg.example/kaapana",
        "REGISTRY_USER": "ci",
        "REGISTRY_TOKEN": "token",
        "REGISTRY_ENV": "DKFZ_CONTAINER_REGISTRY",
        "DEPLOYMENT_INSTANCE_FQDN": "host.inet.dkfz-heidelberg.de",
        "DEPLOYMENT_INSTANCE_USER": "ci-user",
        "DEPLOYMENT_INSTANCE_PLATFORM_PREFIX": "ci-dep",
        "DEPLOYMENT_INSTANCE_SSH_KEY": str(key),
        "CI_COMMIT_BRANCH": "feature/x",
        "CI_COMMIT_TAG": "",
        "CI_PIPELINE_SOURCE": "web",
    }


def run(script, env):
    return subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True, timeout=60)


def test_a_valid_deployment_run_passes(script, env):
    result = run(script, env)
    assert result.returncode == 0, result.stdout
    assert "Preflight OK" in result.stdout


@pytest.mark.parametrize(
    "variable",
    [
        "REGISTRY_URL",
        "REGISTRY_TOKEN",
        "REGISTRY_ENV",
        "DEPLOYMENT_INSTANCE_USER",
        "DEPLOYMENT_INSTANCE_PLATFORM_PREFIX",
        "DOCKER_AUTH_CONFIG",
        "CI_IMAGES_TAG",
    ],
)
def test_an_empty_variable_is_named_in_the_error(script, env, variable):
    env[variable] = ""
    result = run(script, env)
    assert result.returncode == 1
    assert variable in result.stdout


def test_an_empty_ssh_key_file_is_rejected(script, env, tmp_path):
    """require_file, not require: the variable holds a path, and CI hands over
    an empty file when the File-type variable was never filled in."""
    empty = tmp_path / "empty_key"
    empty.touch()
    env["DEPLOYMENT_INSTANCE_SSH_KEY"] = str(empty)
    result = run(script, env)
    assert result.returncode == 1
    assert "DEPLOYMENT_INSTANCE_SSH_KEY(File)" in result.stdout


@pytest.mark.parametrize(
    "prefix,expected",
    [
        ("CI_Dep", "DNS-1123"),
        ("-cidep", "DNS-1123"),
        ("a" * 50, "over the 46"),
    ],
)
def test_a_bad_platform_prefix_is_rejected_before_the_build(script, env, prefix, expected):
    """kaapanactl rejects these too, but only after the whole build has run."""
    env["DEPLOYMENT_INSTANCE_PLATFORM_PREFIX"] = prefix
    result = run(script, env)
    assert result.returncode == 1
    assert expected in result.stdout


def test_an_fqdn_over_the_dcmsend_limit_is_rejected(script, env):
    env["DEPLOYMENT_INSTANCE_FQDN"] = "a" * 58 + ".dkfz.de"
    result = run(script, env)
    assert result.returncode == 1
    assert "57-character dcmsend peerhost limit" in result.stdout


def test_the_registry_host_must_appear_in_docker_auth_config(script, env):
    env["DOCKER_AUTH_CONFIG"] = '{"auths":{"other.example":{}}}'
    result = run(script, env)
    assert result.returncode == 1
    assert "no entry for 'reg.example'" in result.stdout


def test_the_predefined_registry_user_is_rejected(script, env):
    """CI_REGISTRY_USER shadows a GitLab-predefined variable: when the project
    variable is deleted the jobs silently get 'gitlab-ci-token'."""
    env["CI_REGISTRY_USER"] = "gitlab-ci-token"
    result = run(script, env)
    assert result.returncode == 1
    assert "gitlab-ci-token" in result.stdout


def test_half_configured_docker_io_credentials_are_rejected(script, env):
    env["DOCKER_IO_USER"] = "someone"
    result = run(script, env)
    assert result.returncode == 1
    assert "DOCKER_IO_PASSWORD" in result.stdout


def test_a_harvester_run_needs_the_kubeconfig(script, env):
    """No FQDN means a VM is provisioned, which needs Harvester access."""
    env["DEPLOYMENT_INSTANCE_FQDN"] = ""
    result = run(script, env)
    assert result.returncode == 1
    assert "HARVESTER_KUBECONFIG(File)" in result.stdout


def test_deploy_variables_are_not_required_when_not_deploying(tmp_path_factory, env):
    """A tests-only run must not demand the deployment target."""
    config = merged_config(inputs=("exec_deploy=false", "exec_build=false"))
    path = write_script(config, tmp_path_factory.mktemp("preflight_no_deploy"))
    for variable in (
        "DEPLOYMENT_INSTANCE_SSH_KEY",
        "DEPLOYMENT_INSTANCE_USER",
        "REGISTRY_URL",
        "REGISTRY_ENV",
    ):
        env[variable] = ""
    result = run(path, env)
    assert result.returncode == 0, result.stdout


def test_a_release_tag_needs_the_release_registry(script, env):
    env["CI_COMMIT_TAG"] = "0.7.1"
    result = run(script, env)
    assert result.returncode == 1
    assert "RELEASE_REGISTRY_URL" in result.stdout


def test_develop_needs_the_notification_tokens(script, env):
    """Without them a failed develop pipeline reports to nobody."""
    env["CI_COMMIT_BRANCH"] = "develop"
    result = run(script, env)
    assert result.returncode == 1
    for variable in ("GITLAB_API_TOKEN", "SLACK_BOT_TOKEN", "SLACK_CHANNEL_ID"):
        assert variable in result.stdout
