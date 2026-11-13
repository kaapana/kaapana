from typing import Optional
from uuid import uuid4

import pytest
from fastapi import HTTPException
from v1.routers.installation.endpoints import _resolve_install_target
from v1.services.database.models import Extension, ExtensionStatus
from v1.services.oci.models import ExtensionManifest

REPOSITORY_ID = uuid4()
TAG = "my-extension-v1.1.0"


def _active(
    status: ExtensionStatus = ExtensionStatus.INSTALLED,
    version: str = "1.0.0",
    pending_version: Optional[str] = None,
    same_repository: bool = True,
    same_tag: bool = False,
) -> Extension:
    return Extension(
        id=uuid4(),
        repository_id=REPOSITORY_ID if same_repository else uuid4(),
        tag=TAG if same_tag else "my-extension-v1.0.0",
        manifest={"id": str(uuid4()), "name": "my-extension", "version": version, "contents": [], "dependencies": []},
        pending_update={"manifest": {"version": pending_version}} if pending_version else None,
        status=status,
    )


def _resolve(active: Optional[Extension], version: str):
    manifest = ExtensionManifest(id=uuid4(), name="my-extension", version=version, contents=[], dependencies=[])
    return _resolve_install_target(active, REPOSITORY_ID, TAG, manifest)


def _conflict(match: str):
    return pytest.raises(HTTPException, match=f"^409: .*{match}")


def test_no_active_extension_is_installed():
    assert _resolve(None, "1.0.0") is None


@pytest.mark.parametrize("version", ["1.0", "v1.0.0", "latest"])
def test_invalid_version_is_rejected(version: str):
    with pytest.raises(HTTPException) as e:
        _resolve(None, version)
    assert e.value.status_code == 400


def test_higher_version_from_the_same_repository_updates():
    active = _active()
    assert _resolve(active, "1.1.0") == active.id


@pytest.mark.parametrize("status", [ExtensionStatus.INSTALLED, ExtensionStatus.UPDATE_FAILED])
def test_version_from_another_repository_conflicts(status: ExtensionStatus):
    active = _active(status, pending_version="2.0.0", same_repository=False)
    with _conflict("from another repository"):
        _resolve(active, "2.1.0")


def test_same_version_under_another_tag_conflicts():
    with _conflict("already installed in version 1.0.0"):
        _resolve(_active(), "1.0.0")


def test_lower_version_conflicts():
    with _conflict("downgrading"):
        _resolve(_active(version="2.0.0"), "1.0.0")


@pytest.mark.parametrize("requested", ["2.0.0", "2.0.1"])
def test_update_failed_retries_or_moves_to_a_newer_target(requested: str):
    active = _active(ExtensionStatus.UPDATE_FAILED, pending_version="2.0.0")
    assert _resolve(active, requested) == active.id


def test_update_failed_rejects_a_version_below_the_failed_target():
    active = _active(ExtensionStatus.UPDATE_FAILED, pending_version="2.0.0")
    with _conflict("update to 2.0.0 failed"):
        _resolve(active, "1.5.0")


def test_update_failed_rejects_the_installed_version():
    active = _active(ExtensionStatus.UPDATE_FAILED, pending_version="2.0.0")
    with _conflict("already installed in version 1.0.0"):
        _resolve(active, "1.0.0")


@pytest.mark.parametrize("status", list(ExtensionStatus))
def test_the_same_repository_and_tag_takes_the_install_path(status: ExtensionStatus):
    active = _active(status, same_tag=True)
    assert _resolve(active, "1.0.0") is None


@pytest.mark.parametrize(
    "status", [ExtensionStatus.INSTALLATION_FAILED, ExtensionStatus.UPDATING, ExtensionStatus.UNINSTALLING]
)
@pytest.mark.parametrize(("same_repository", "same_tag"), [(True, False), (False, True), (False, False)])
def test_other_status_with_another_repository_or_tag_conflicts(
    status: ExtensionStatus, same_repository: bool, same_tag: bool
):
    active = _active(status, same_repository=same_repository, same_tag=same_tag)
    with _conflict("Uninstall it first"):
        _resolve(active, "1.1.0")
