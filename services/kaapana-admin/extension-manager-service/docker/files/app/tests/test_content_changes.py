from uuid import uuid4

import pytest
from v1.services.content_changes import (
    ContentAction,
    ContentTypeChangedError,
    InstalledContentState,
    plan_content_changes,
)
from v1.services.database.models import ContentStatus
from v1.services.oci.models import Content, ExtensionManifest


def _manifest(version: str, contents: dict[str, str]) -> ExtensionManifest:
    return ExtensionManifest(
        id=uuid4(),
        name="extension",
        version=version,
        contents=[Content(name=name, contentType=content_type, files=[]) for name, content_type in contents.items()],
        dependencies=[],
    )


def _installed(name: str, version: str | None = "1.0.0", status: ContentStatus = ContentStatus.INSTALLED):
    return InstalledContentState(name=name, content_type="workflow-v1", status=status, applied_version=version)


def test_update_installs_changes_and_removes_contents():
    target = _manifest("2.0.0", {"kept": "workflow-v1", "added": "workflow-v1"})

    changes = plan_content_changes([_installed("kept"), _installed("removed")], target)

    assert changes == [
        ("kept", ContentAction.UPDATE),
        ("added", ContentAction.INSTALL),
        ("removed", ContentAction.UNINSTALL),
    ]


def test_retry_only_touches_what_is_still_old():
    target = _manifest("2.0.0", {"updated": "workflow-v1", "failed": "workflow-v1", "added": "workflow-v1"})
    installed = [
        _installed("updated", version="2.0.0"),
        _installed("failed", version="1.0.0", status=ContentStatus.INSTALLED),
        _installed("added", version=None, status=ContentStatus.INSTALLATION_FAILED),
        _installed("removed", version="1.0.0", status=ContentStatus.UNINSTALLED),
    ]

    changes = plan_content_changes(installed, target)

    assert changes == [
        ("updated", ContentAction.SKIP),
        ("failed", ContentAction.UPDATE),
        ("added", ContentAction.INSTALL),
        ("removed", ContentAction.SKIP),
    ]


def test_content_that_comes_back_is_installed_again():
    target = _manifest("2.0.0", {"returning": "workflow-v1"})

    changes = plan_content_changes([_installed("returning", status=ContentStatus.UNINSTALLED)], target)

    assert changes == [("returning", ContentAction.INSTALL)]


def test_content_type_change_is_rejected():
    target = _manifest("2.0.0", {"content": "helm-chart-v1"})

    with pytest.raises(ContentTypeChangedError):
        plan_content_changes([_installed("content")], target)
