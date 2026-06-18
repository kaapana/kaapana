"""
Structural guards for the Keycloak bootstrap + setup charts.
Structural guards for the Keycloak bootstrap + setup charts.

Scope: chart structure, file presence, and Helm template / source content only.
Scope: chart structure, file presence, and Helm template / source content only.
These guards catch configuration regressions that would silently break a
deploy — missing files, wrong annotations, forbidden env vars in Helm
template files. They do NOT prove correct runtime behaviour; use the unit tests
below for that:

  keycloak-setup/tests/test_bootstrap_admin_client.py
  keycloak-setup/tests/test_configure_realm.py
  keycloak-setup/tests/test_bootstrap_admin_client.py
  keycloak-setup/tests/test_configure_realm.py
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

KEYCLOAK_SETUP = ROOT / "services/kaapana-admin/keycloak/keycloak-setup"
SETUP_CHART = KEYCLOAK_SETUP / "keycloak-setup-chart"
BOOTSTRAP_CHART = KEYCLOAK_SETUP / "keycloak-bootstrap-chart"
DOCKER_FILES = KEYCLOAK_SETUP / "docker/files"

SETUP_JOB = SETUP_CHART / "templates/keycloak-setup-job.yaml"
BOOTSTRAP_JOB = BOOTSTRAP_CHART / "templates/keycloak-bootstrap-job.yaml"
ADMIN_PASSWORD_SECRET = BOOTSTRAP_CHART / "templates/kaapana-admin-password.yaml"

# Rotating secrets: regenerated per deploy, the setup job re-syncs them into Keycloak.
ROTATING_SECRET_TEMPLATES = [
    SETUP_CHART / "templates/kaapana-service-password.yaml",
    SETUP_CHART / "templates/system-user-password.yaml",
KEYCLOAK_SETUP = ROOT / "services/kaapana-admin/keycloak/keycloak-setup"
SETUP_CHART = KEYCLOAK_SETUP / "keycloak-setup-chart"
BOOTSTRAP_CHART = KEYCLOAK_SETUP / "keycloak-bootstrap-chart"
DOCKER_FILES = KEYCLOAK_SETUP / "docker/files"

SETUP_JOB = SETUP_CHART / "templates/keycloak-setup-job.yaml"
BOOTSTRAP_JOB = BOOTSTRAP_CHART / "templates/keycloak-bootstrap-job.yaml"
ADMIN_PASSWORD_SECRET = BOOTSTRAP_CHART / "templates/kaapana-admin-password.yaml"

# Rotating secrets: regenerated per deploy, the setup job re-syncs them into Keycloak.
ROTATING_SECRET_TEMPLATES = [
    SETUP_CHART / "templates/kaapana-service-password.yaml",
    SETUP_CHART / "templates/system-user-password.yaml",
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

KEYCLOAK_HELPER_SOURCES = [
    ROOT / p
    for p in [
        "services/data-separation/access-information-interface/docker/backend/files/app/keycloak_helper.py",
        "services/data-separation/access-information-interface/docker/init-project/files/KeycloakHelper.py",
        "services/data-separation/project-namespace/docker/files/KeycloakHelper.py",
    ]
]

KEYCLOAK_HELPER_SOURCES = [
    ROOT / p
    for p in [
        "services/data-separation/access-information-interface/docker/backend/files/app/keycloak_helper.py",
        "services/data-separation/access-information-interface/docker/init-project/files/KeycloakHelper.py",
        "services/data-separation/project-namespace/docker/files/KeycloakHelper.py",
    ]
]


def _read(path: Path) -> str:
    assert path.is_file(), f"expected file is missing: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


# --- Chart structure ----------------------------------------------------------


@pytest.mark.parametrize("job", [SETUP_JOB, BOOTSTRAP_JOB], ids=lambda p: p.name)
def test_jobs_have_no_helm_hook(job):
    text = _read(job)
@pytest.mark.parametrize("job", [SETUP_JOB, BOOTSTRAP_JOB], ids=lambda p: p.name)
def test_jobs_have_no_helm_hook(job):
    text = _read(job)
    assert "helm.sh/hook" not in text, (
        f"{job.name} must be a plain Job, not a helm hook — a hook blocks helm "
        "install while waiting on Keycloak cold-boot, causing a timeout."
        f"{job.name} must be a plain Job, not a helm hook — a hook blocks helm "
        "install while waiting on Keycloak cold-boot, causing a timeout."
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


def test_admin_chart_includes_bootstrap_chart():
    text = _read(ROOT / "platforms/kaapana-admin-chart/requirements.yaml")
    assert "keycloak-bootstrap-chart" in text, (
        "keycloak-bootstrap-chart must be a dependency of the kaapana-admin chart, "
        "otherwise the kaapana-admin client is never created."
    )


def test_admin_chart_includes_bootstrap_chart():
    text = _read(ROOT / "platforms/kaapana-admin-chart/requirements.yaml")
    assert "keycloak-bootstrap-chart" in text, (
        "keycloak-bootstrap-chart must be a dependency of the kaapana-admin chart, "
        "otherwise the kaapana-admin client is never created."
    )


def test_configmap_references_kaapana_service_json():
    text = _read(SETUP_CHART / "templates/realm-objects-configmap.yaml")
    text = _read(SETUP_CHART / "templates/realm-objects-configmap.yaml")
    assert "kaapana-service.json" in text, (
        "realm-objects-configmap must mount kaapana-service.json, otherwise "
        "configure_realm.py raises FileNotFoundError at runtime."
    )


def test_kaapana_service_realm_object_exists():
    path = SETUP_CHART / "realm_objects/kaapana-service.json"
    path = SETUP_CHART / "realm_objects/kaapana-service.json"
    assert path.is_file(), f"missing realm object: {path.relative_to(ROOT)}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("clientId") == "kaapana-service"
    assert data.get("serviceAccountsEnabled") is True


# --- Secret persistence: only kaapana-admin-password is persisted -------------
# --- Secret persistence: only kaapana-admin-password is persisted -------------


def test_admin_password_secret_has_resource_policy_keep():
    text = _read(ADMIN_PASSWORD_SECRET)
def test_admin_password_secret_has_resource_policy_keep():
    text = _read(ADMIN_PASSWORD_SECRET)
    assert "helm.sh/resource-policy: keep" in text, (
        "kaapana-admin-password is the only persisted credential and must carry "
        "resource-policy: keep so it survives helm uninstall."
        "kaapana-admin-password is the only persisted credential and must carry "
        "resource-policy: keep so it survives helm uninstall."
    )


def test_admin_password_secret_lookup_uses_admin_namespace():
    text = _read(ADMIN_PASSWORD_SECRET)
def test_admin_password_secret_lookup_uses_admin_namespace():
    text = _read(ADMIN_PASSWORD_SECRET)
    assert ".Values.global.admin_namespace" in text, (
        "kaapana-admin-password lookup must use .Values.global.admin_namespace — "
        "the release namespace differs from the admin resource namespace."
        "kaapana-admin-password lookup must use .Values.global.admin_namespace — "
        "the release namespace differs from the admin resource namespace."
    )
    assert (
        ".Release.Namespace" not in text
    ), "kaapana-admin-password must not use .Release.Namespace in the lookup."


@pytest.mark.parametrize("template", ROTATING_SECRET_TEMPLATES, ids=lambda p: p.name)
def test_rotating_secrets_are_not_persisted(template):
    text = _read(template)
    assert "helm.sh/resource-policy: keep" not in text, (
        f"{template.name} must NOT carry resource-policy: keep — it is regenerated "
        "per deploy and re-synced into Keycloak by the setup job (no drift)."
    )


# --- Admin password only in the bootstrap job, never in the setup job ----------


def test_bootstrap_job_carries_admin_password():
    text = _read(BOOTSTRAP_JOB)
    assert (
        "credentials_keycloak_admin_password" in text
    ), "bootstrap job needs the admin password for the initial bootstrap."
    assert (
        "KAAPANA_ADMIN_CLIENT_SECRET" in text
    ), "bootstrap job must mount the kaapana-admin client secret."


def test_setup_job_has_no_admin_password():
    text = _read(SETUP_JOB)
    assert "credentials_keycloak_admin_password" not in text, (
        "setup job must NOT receive the admin password — it authenticates as the "
        "kaapana-admin client (client_credentials)."
    )
    assert (
        "KEYCLOAK_PASSWORD" not in text
    ), "setup job must not carry KEYCLOAK_PASSWORD."
    assert (
        "KAAPANA_ADMIN_CLIENT_SECRET" in text
    ), "setup job must authenticate via the kaapana-admin client secret."


# --- configure_realm.py authenticates as kaapana-admin (no admin password) -----


def test_configure_realm_uses_kaapana_admin_client_credentials():
    text = _read(DOCKER_FILES / "configure_realm.py")
    assert "from_client_credentials" in text and '"kaapana-admin"' in text, (
        "configure_realm.py must authenticate as the kaapana-admin client via "
        "client_credentials."
    )
    assert (
        "from_admin_password" not in text
    ), "configure_realm.py must not use the admin password grant."
    # The kaapana-service role set (without manage-clients) is asserted behaviorally
    # in test_configure_realm.py::test_service_account_roles_exclude_manage_clients.


def test_bootstrap_script_is_admin_client_first():
    text = _read(DOCKER_FILES / "bootstrap_admin_client.py")
    assert (
        "_admin_client_functional" in text
    ), "bootstrap must check the admin client first (skip when it already works)."
    assert (
        "from_admin_password" in text
    ), "bootstrap must fall back to the admin password when the client is missing."


# --- Migration script: minimal roles, no manage-clients -----------------------


def test_migration_script_assigns_minimal_roles_without_manage_clients():
    text = _read(ROOT / "platforms/migrate_keycloak_service_client.sh")
    for role in ('"manage-users"', '"query-users"', '"query-groups"', '"view-realm"'):
        assert role in text, f"migration script must assign the {role} role."
    assert (
        '"manage-clients"' not in text
    ), "migration script must not assign manage-clients to kaapana-service."


# --- KeycloakHelper copies must not use password grant or master realm --------


@pytest.mark.parametrize("source", KEYCLOAK_HELPER_SOURCES, ids=lambda p: p.parent.name)
def test_keycloak_helpers_do_not_use_admin_credentials(source):
    text = _read(source)
    assert (
        '"grant_type": "password"' not in text
    ), f"{source.name} must not use the password grant."
    assert (
        "realms/master" not in text
    ), f"{source.name} must not authenticate against the master realm."
    assert (
        "KEYCLOAK_USER" not in text and "KEYCLOAK_PASSWORD" not in text
    ), f"{source.name} must not read admin credentials from env."
    assert (
        "master_access_token" not in text
    ), f"{source.name} must not use master_access_token — use service_access_token."


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
