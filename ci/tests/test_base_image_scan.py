import importlib.util
from pathlib import Path

import pytest
import yaml
from conftest import jobs

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "ci" / "ci-code" / "security" / "base_image_scan.py"


@pytest.fixture(scope="module")
def scan():
    spec = importlib.util.spec_from_file_location("base_image_scan", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(root, path, content):
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content)


def test_from_images_skips_local_images_stages_and_args(scan, tmp_path):
    write(
        tmp_path,
        "Dockerfile",
        "ARG BASE=ubuntu:24.04\n"
        "FROM --platform=linux/amd64 docker.io/node:26-alpine3.24 AS build-stage\n"
        "FROM build-stage AS test\n"
        "FROM local-only/base-python-cpu:latest\n"
        "FROM ${BASE}\n"
        "from docker.io/library/nginx:1.31-alpine3.24\n",
    )
    assert scan.from_images(tmp_path / "Dockerfile") == ["node:26-alpine3.24", "nginx:1.31-alpine3.24"]


def test_base_images_takes_base_images_and_node_and_nginx_of_services(scan, tmp_path):
    write(tmp_path, "data-processing/base-images/base-python-cpu/Dockerfile", "FROM ubuntu:24.04\n")
    write(
        tmp_path,
        "services/base/portal-ui/docker/Dockerfile",
        "FROM docker.io/node:26-alpine3.24 AS build\nFROM nginxinc/nginx-unprivileged:1.31-alpine\n",
    )
    write(tmp_path, "services/base/other-ui/docker/Dockerfile", "FROM node:26-alpine3.24\n")
    write(tmp_path, "services/store/redis/docker/Dockerfile", "FROM docker.io/redis:7.4-alpine\n")
    write(tmp_path, "services/applications/jupyterlab/docker/Dockerfile", "FROM nginx:1.30-alpine\n")
    write(tmp_path, "services/meta/os-dashboards/docker/os-dashboard/Dockerfile", "FROM docker.io/node:22.15.0\n")
    assert scan.base_images(tmp_path) == [
        "nginxinc/nginx-unprivileged:1.31-alpine",
        "node:26-alpine3.24",
        "ubuntu:24.04",
    ]


def test_the_repository_has_base_images_to_scan(scan):
    images = scan.base_images()
    assert "ubuntu:24.04" in images
    assert any(scan.repository_name(image) == "nginx-unprivileged" for image in images)
    assert "node:22.15.0" not in images


def test_every_ignored_vulnerability_expires_and_has_a_reason():
    ignore_file = REPO / ".trivyignore.yaml"
    if not ignore_file.exists():
        pytest.skip("no ignored vulnerabilities")
    entries = yaml.safe_load(ignore_file.read_text()).get("vulnerabilities") or []
    assert all(entry.get("expired_at") and entry.get("statement") for entry in entries), entries


def test_base_image_scan_runs_alone_on_schedules(default_config):
    job = jobs(default_config)["base_image_scan"]
    assert job["needs"] == []
    assert any(rule.get("if") == '$CI_PIPELINE_SOURCE == "schedule"' for rule in job["rules"])
    assert "ci/ci-code/security/base_image_scan.py" in " ".join(job["script"])
