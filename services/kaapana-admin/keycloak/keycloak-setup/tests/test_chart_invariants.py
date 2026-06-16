"""
Structural guards for the Keycloak setup chart.

Scope: chart structure, file presence, and Helm template content only.
These guards catch configuration regressions that would silently break a
deploy — missing files, wrong annotations, forbidden env vars in Helm
template files. They do NOT prove correct runtime behaviour; use the unit tests
below for that:

  services/data-separation/access-information-interface/docker/backend/files/tests/test_keycloak_helper.py
  services/base/kaapana-backend/docker/files/tests/test_user_service.py

No cluster, no Keycloak, no network required.

Run from anywhere:
    pytest services/kaapana-admin/keycloak/keycloak-setup/tests/test_chart_invariants.py
"""

import json
from pathlib import Path

import pytest


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "platforms").is_dir() and (parent / "services").is_dir():
            return parent
    raise RuntimeError("repo root not found")


ROOT = _repo_root()

KEYCLOAK_SETUP_CHART = (
    ROOT / "services/kaapana-admin/keycloak/keycloak-setup/keycloak-setup-chart"
)

ADMIN_SECRET_TEMPLATES = [
    KEYCLOAK_SETUP_CHART / "templates/kaapana-service-password.yaml",
    KEYCLOAK_SETUP_CHART / "templates/system-user-password.yaml",
]

RUNTIME_TEMPLATES = [
    ROOT / p
    for p in [
        "services/base/kaapana-backend/kaapana-backend-chart/templates/deployment.yaml",
        "services/data-separation/access-information-interface/access-information-interface-chart/templates/deployment.yaml",
        "services/data-separation/access-information-interface/access-information-interface-chart/templates/init_project.yaml",
        "services/data-separation/project-namespace/project-namespace-chart/templates/create-project-user.yaml",
    ]
]


def _read(path: Path) -> str:
    assert path.is_file(), f"expected file is missing: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


# --- Chart structure ----------------------------------------------------------


def test_keycloak_setup_job_has_no_helm_hook():
    text = _read(KEYCLOAK_SETUP_CHART / "templates/keycloak-setup-job.yaml")
    assert "helm.sh/hook" not in text, (
        "keycloak-setup must be a plain Job, not a helm hook — a hook blocks "
        "helm install while waiting on Keycloak cold-boot, causing a timeout."
    )


def test_services_namespace_includes_service_password_chart():
    text = _read(
        ROOT
        / "platforms/kaapana-platform-chart/deps/services-namespace/requirements.yaml"
    )
    assert "kaapana-service-password-chart" in text, (
        "kaapana-service-password-chart must be a dependency of the "
        "services-namespace, otherwise the services-namespace secret is never created."
    )


def test_configmap_references_kaapana_service_json():
    text = _read(KEYCLOAK_SETUP_CHART / "templates/realm-objects-configmap.yaml")
    assert "kaapana-service.json" in text, (
        "realm-objects-configmap must mount kaapana-service.json, otherwise "
        "configure_realm.py raises FileNotFoundError at runtime."
    )


def test_kaapana_service_realm_object_exists():
    path = KEYCLOAK_SETUP_CHART / "realm_objects/kaapana-service.json"
    assert path.is_file(), f"missing realm object: {path.relative_to(ROOT)}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("clientId") == "kaapana-service"
    assert data.get("serviceAccountsEnabled") is True


# --- Secret template invariants -----------------------------------------------


@pytest.mark.parametrize("template", ADMIN_SECRET_TEMPLATES, ids=lambda p: p.name)
def test_admin_secret_has_resource_policy_keep(template):
    text = _read(template)
    assert "helm.sh/resource-policy: keep" in text, (
        f"{template.name} must carry resource-policy: keep so the secret "
        "survives helm uninstall and is not regenerated on the next deploy."
    )


@pytest.mark.parametrize("template", ADMIN_SECRET_TEMPLATES, ids=lambda p: p.name)
def test_admin_secret_lookup_uses_admin_namespace(template):
    text = _read(template)
    assert ".Values.global.admin_namespace" in text, (
        f"{template.name} lookup must use .Values.global.admin_namespace — "
        "the Helm release namespace differs from the admin resource namespace, "
        "so using .Release.Namespace causes a new random secret on every deploy "
        "and desyncs Keycloak from the K8s secret."
    )
    assert (
        ".Release.Namespace" not in text
    ), f"{template.name} must not use .Release.Namespace in the secret lookup."


# --- Runtime templates must not carry admin credentials -----------------------


@pytest.mark.parametrize(
    "template",
    RUNTIME_TEMPLATES,
    ids=lambda p: str(p.parent.parent.name) + "/" + p.name,
)
def test_runtime_templates_drop_admin_password(template):
    text = _read(template)
    assert (
        "KEYCLOAK_ADMIN_PASSWORD" not in text
    ), f"{template.name} must not inject KEYCLOAK_ADMIN_PASSWORD."
    assert (
        "credentials_keycloak_admin_password" not in text
    ), f"{template.name} must not reference the admin password helm value."
    assert (
        "kaapana-service-password" in text
    ), f"{template.name} must mount the kaapana-service-password secret."
