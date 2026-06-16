"""
Structural regression guards for the Keycloak service-client changeover (#1918).

These tests parse chart templates and source files directly — no cluster, no
Keycloak. Each guard corresponds to a deploy bug that was "implemented" but
silently incomplete during #1918, so that the same gap cannot reappear
unnoticed.

Run from anywhere:
    pytest services/kaapana-admin/keycloak/keycloak-setup/tests/test_chart_invariants.py
"""

from pathlib import Path

import pytest


def _repo_root() -> Path:
    """Walk up until we find the directory that holds both platforms/ and services/."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "platforms").is_dir() and (parent / "services").is_dir():
            return parent
    raise RuntimeError("repo root (with platforms/ and services/) not found")


ROOT = _repo_root()

KEYCLOAK_SETUP_CHART = (
    ROOT / "services/kaapana-admin/keycloak/keycloak-setup/keycloak-setup-chart"
)
ADMIN_SECRET_TEMPLATES = [
    KEYCLOAK_SETUP_CHART / "templates/kaapana-service-password.yaml",
    KEYCLOAK_SETUP_CHART / "templates/system-user-password.yaml",
]
# Runtime services that must NOT carry the admin password anymore. The
# keycloak-setup *bootstrap* job legitimately keeps admin credentials and is
# excluded on purpose.
RUNTIME_TEMPLATES = [
    ROOT
    / "services/base/kaapana-backend/kaapana-backend-chart/templates/deployment.yaml",
    ROOT
    / "services/data-separation/access-information-interface/access-information-interface-chart/templates/deployment.yaml",
    ROOT
    / "services/data-separation/access-information-interface/access-information-interface-chart/templates/init_project.yaml",
    ROOT
    / "services/data-separation/project-namespace/project-namespace-chart/templates/create-project-user.yaml",
]
KEYCLOAK_HELPER_SOURCES = [
    ROOT
    / "services/data-separation/access-information-interface/docker/backend/files/app/keycloak_helper.py",
    ROOT
    / "services/data-separation/access-information-interface/docker/init-project/files/KeycloakHelper.py",
    ROOT / "services/data-separation/project-namespace/docker/files/KeycloakHelper.py",
]


def _read(path: Path) -> str:
    assert path.is_file(), f"expected file is missing: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


# --- F1: keycloak-setup must be a plain Job, not a blocking helm hook ---------


def test_keycloak_setup_job_has_no_helm_hook():
    text = _read(KEYCLOAK_SETUP_CHART / "templates/keycloak-setup-job.yaml")
    assert "helm.sh/hook" not in text, (
        "keycloak-setup must be a plain Job, not a helm hook — a hook blocks "
        "helm install while waiting on the Keycloak cold-boot (context deadline "
        "exceeded). See #1918 follow-up."
    )


# --- F2: services-namespace secret chart must be wired in ---------------------


def test_services_namespace_includes_service_password_chart():
    text = _read(
        ROOT
        / "platforms/kaapana-platform-chart/deps/services-namespace/requirements.yaml"
    )
    assert "kaapana-service-password-chart" in text, (
        "kaapana-service-password-chart must be a dependency of the "
        "services-namespace, otherwise the services-namespace secret is never "
        "created (orphaned chart)."
    )


# --- F4: realm-objects configmap must ship the service-client definition ------


def test_configmap_references_kaapana_service_json():
    text = _read(KEYCLOAK_SETUP_CHART / "templates/realm-objects-configmap.yaml")
    assert "kaapana-service.json" in text, (
        "realm-objects-configmap must mount kaapana-service.json, otherwise "
        "configure_realm.py fails with FileNotFoundError."
    )


def test_kaapana_service_realm_object_exists():
    path = KEYCLOAK_SETUP_CHART / "realm_objects/kaapana-service.json"
    assert path.is_file(), f"missing realm object: {path.relative_to(ROOT)}"
    assert '"clientId": "kaapana-service"' in _read(path)


# --- F3: admin-namespace secrets must survive a redeploy ----------------------


@pytest.mark.parametrize("template", ADMIN_SECRET_TEMPLATES, ids=lambda p: p.name)
def test_admin_secret_has_resource_policy_keep(template):
    text = _read(template)
    assert "helm.sh/resource-policy: keep" in text, (
        f"{template.name} must carry resource-policy: keep so reuse/redeploy "
        "does not regenerate the secret and desync the Keycloak client / "
        "project namespaces."
    )


# --- F6: secret lookups must target admin_namespace, not .Release.Namespace ---


@pytest.mark.parametrize("template", ADMIN_SECRET_TEMPLATES, ids=lambda p: p.name)
def test_admin_secret_lookup_uses_admin_namespace(template):
    text = _read(template)
    assert ".Values.global.admin_namespace" in text, (
        f"{template.name} lookup must use .Values.global.admin_namespace, not "
        ".Release.Namespace — the Helm release namespace is 'default' but the "
        "secret lives in the admin namespace. Wrong namespace causes a new random "
        "secret on every deploy, desyncing Keycloak and K8s (bug F6 in #1918)."
    )
    assert (
        ".Release.Namespace" not in text
    ), f"{template.name} must not use .Release.Namespace in the secret lookup."


# --- Fallback: configure_realm.py must sync dynamic secrets via service token --


def test_configure_realm_has_manage_clients_role():
    text = _read(
        ROOT
        / "services/kaapana-admin/keycloak/keycloak-setup/docker/files/configure_realm.py"
    )
    assert '"manage-clients"' in text, (
        "configure_realm.py must assign the manage-clients role to the "
        "kaapana-service service account so the fallback path can update the "
        "OIDC client secret without admin credentials."
    )


def test_configure_realm_fallback_syncs_oidc_and_system_user():
    text = _read(
        ROOT
        / "services/kaapana-admin/keycloak/keycloak-setup/docker/files/configure_realm.py"
    )
    assert "_update_oidc_client_secret" in text, (
        "configure_realm.py fallback must call _update_oidc_client_secret — "
        "deploy_platform.sh regenerates OIDC_CLIENT_SECRET on every run, so "
        "the fallback path must push the new value into Keycloak."
    )
    assert "_reset_system_user_password" in text, (
        "configure_realm.py fallback must call _reset_system_user_password — "
        "the system user password can diverge between K8s secret and Keycloak "
        "after failed deploys."
    )


# --- Core #1918 criterion: runtime services no longer use the admin password --


@pytest.mark.parametrize(
    "template",
    RUNTIME_TEMPLATES,
    ids=lambda p: str(p.parent.parent.name) + "/" + p.name,
)
def test_runtime_templates_drop_admin_password(template):
    text = _read(template)
    assert (
        "KEYCLOAK_ADMIN_PASSWORD" not in text
    ), f"{template.name} must not inject KEYCLOAK_ADMIN_PASSWORD anymore (#1918)."
    assert (
        "credentials_keycloak_admin_password" not in text
    ), f"{template.name} must not reference the admin password helm value."
    assert (
        "kaapana-service-password" in text
    ), f"{template.name} must mount the kaapana-service-password secret."


# --- Core #1918 criterion: helpers use client_credentials, not password grant -


@pytest.mark.parametrize("source", KEYCLOAK_HELPER_SOURCES, ids=lambda p: p.name)
def test_keycloak_helpers_use_client_credentials(source):
    text = _read(source)
    assert '"grant_type": "client_credentials"' in text
    assert '"client_id": "kaapana-service"' in text
    assert (
        '"grant_type": "password"' not in text
    ), f"{source.name} must not fall back to the password grant."
    assert (
        "realms/master" not in text
    ), f"{source.name} must target the kaapana realm, not master."


def test_kaapana_backend_user_service_uses_service_client():
    text = _read(
        ROOT / "services/base/kaapana-backend/docker/files/app/users/services.py"
    )
    assert 'client_id="kaapana-service"' in text
    assert "client_secret_key=self.client_secret" in text
    assert (
        "master" not in text
    ), "UserService must authenticate against the kaapana realm, not master."


def test_oidc_logout_uses_client_credentials():
    text = _read(
        ROOT / "services/base/kaapana-backend/docker/files/app/admin/routers.py"
    )
    assert '"grant_type": "client_credentials"' in text
    assert "realms/kaapana/protocol/openid-connect/token" in text
