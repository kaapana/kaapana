"""Shared fixtures for the CI configuration tests.

These tests read the pipeline as GitLab would see it. The merged config is
produced by gitlab-ci-local (`--preview` resolves `spec:inputs` and the
`include:` tree, which `glab ci lint` cannot), so every assertion is about the
config that ships, not a copy of it.

Everything here runs locally:

    pytest ci/tests

gitlab-ci-local must be on PATH; all tests fail if it is missing.
"""

import functools
import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

GITLAB_CI_LOCAL = shutil.which("gitlab-ci-local")

DEPLOY_INPUTS = ("exec_deploy=true", "exec_build=false", "exec_unit_tests=false")
FQDN = "DEPLOYMENT_INSTANCE_FQDN:host.inet.dkfz-heidelberg.de"


@pytest.fixture(scope="session", autouse=True)
def _require_gitlab_ci_local():
    if GITLAB_CI_LOCAL is None:
        pytest.fail("gitlab-ci-local not on PATH (npm install -g gitlab-ci-local)")


@pytest.fixture(scope="session")
def readiness():
    """target_readiness.py loaded as a module, for monkeypatched checks."""
    module_path = Path(__file__).resolve().parents[1] / "ci-code" / "deploy" / "target_readiness.py"
    spec = importlib.util.spec_from_file_location("target_readiness", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@functools.lru_cache(maxsize=None)
def merged_config(inputs=(), variables=()):
    """The whole pipeline as GitLab would build it, for one set of inputs.

    `inputs` and `variables` are tuples of "name=value" / "name:value" so the
    result can be cached; each call costs a subprocess.
    """
    cmd = [GITLAB_CI_LOCAL, "--preview", "--variable", "CI_PIPELINE_SOURCE=web"]
    for item in inputs:
        cmd += ["--input", item]
    for item in variables:
        cmd += ["--variable", item]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise AssertionError(f"gitlab-ci-local failed:\n{result.stderr or result.stdout}")
    lines = result.stdout.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.startswith(("stages:", "default:", "workflow:"))),
        None,
    )
    if start is None:
        raise AssertionError(f"no config in gitlab-ci-local output:\n{result.stdout[:500]}")
    return yaml.safe_load("\n".join(lines[start:]))


def jobs(config):
    """Job name -> definition, without the top-level keys of the config."""
    reserved = {"stages", "variables", "workflow", "default", "include", "spec"}
    return {
        name: body
        for name, body in config.items()
        if name not in reserved and not name.startswith(".") and isinstance(body, dict)
    }


@pytest.fixture(scope="session")
def default_config():
    return merged_config()
