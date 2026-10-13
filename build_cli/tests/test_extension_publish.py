import hashlib
import json
import tarfile
from unittest.mock import patch

import httpx
import pytest
from build_cli.build import IssueTracker
from build_cli.container import Status
from build_cli.extension import ExtensionHelper
from build_cli.extension.extension import ExtensionUtilityLibrary
from factories import container, image_line, write_extension
from kaapana_containers.registries.registry import OCIError


class FakeRegistry:
    """Stores pushed extensions like a registry, and records how the build talks to it."""

    def __init__(self):
        self.tags: dict[str, dict] = {}
        self.pushed: list[str] = []
        self.clients: list[tuple[str, str, str, str]] = []
        self.get_error: Exception | None = None


@pytest.fixture
def registry():
    fake = FakeRegistry()

    class FakeClient(ExtensionUtilityLibrary):
        def __init__(self, registry, repo, username, password):
            fake.clients.append((registry, repo, username, password))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, tag):
            if fake.get_error:
                raise fake.get_error
            if tag not in fake.tags:
                raise OCIError("manifest unknown", code="MANIFEST_UNKNOWN")
            return fake.tags[tag]

        async def push(self, ext_path, bump=None, overwrite=False):
            # Store the same metadata as the real push: the manifest and the digest of every file.
            with tarfile.open(ext_path) as tar:
                files = {member.name: tar.extractfile(member).read() for member in tar.getmembers() if member.isfile()}
            manifest = json.loads(files.pop("extension_manifest.json"))
            tag = f"{manifest['id']}-v{manifest['version']}"
            fake.tags[tag] = {
                "user_metadata": {"extension_manifest": manifest, "apiVersion": "v1"},
                "files": [
                    {"filename": name, "digest": f"sha256:{hashlib.sha256(data).hexdigest()}"}
                    for name, data in files.items()
                ],
            }
            fake.pushed.append(tag)
            return tag

    with patch("build_cli.extension.extension_helper.ExtensionUtilityLibrary", FakeClient):
        yield fake


@pytest.fixture
def dummy(kaapana_dir, build_state):
    """The dummy extension, selected for publishing, with its image pushed."""
    manifest_path = write_extension(kaapana_dir, "dummy", dag=image_line("dummy"))
    image = container("dummy")
    image.status = Status.PUSHED
    build_state.containers_available = {image}
    ExtensionHelper.collect_extensions()
    ExtensionHelper.resolve_extension_containers()
    build_state.selected_extensions = set(build_state.extensions_available)
    extension = next(iter(build_state.extensions_available))
    return extension, image, manifest_path


def archives(build_config) -> list[str]:
    output = build_config.build_dir / "extensions"
    return sorted(path.name for path in output.glob("*.tar.gz")) if output.exists() else []


@pytest.mark.parametrize(
    ("default_registry", "plain_http", "expected"),
    [
        ("registry.hzdr.de/kaapana/kaapana", False, ("https://registry.hzdr.de", "kaapana/kaapana/extensions")),
        ("localhost:5000", True, ("http://localhost:5000", "extensions")),
        ("http://localhost:5000/kaapana/", False, ("http://localhost:5000", "kaapana/extensions")),
    ],
)
def test_registry_location(build_config, default_registry, plain_http, expected):
    build_config.default_registry = default_registry
    build_config.plain_http = plain_http

    assert ExtensionHelper.registry_location() == expected


def test_pushes_a_new_extension(build_config, registry, dummy):
    extension, _, _ = dummy
    build_config.registry_username = "user"
    build_config.registry_password = "secret"

    ExtensionHelper.build_and_push_extensions()

    assert registry.pushed == [extension.tag]
    assert registry.clients == [("https://registry.example.com", "kaapana/extensions", "user", "secret")]
    assert archives(build_config) == ["dummy-extension-v0.1.0.tar.gz"]
    assert IssueTracker.issues == []


def test_does_not_push_the_same_content_twice(registry, dummy):
    ExtensionHelper.build_and_push_extensions()
    ExtensionHelper.build_and_push_extensions()

    assert len(registry.pushed) == 1
    assert IssueTracker.issues == []


def test_refuses_to_change_a_published_version(registry, dummy):
    _, _, manifest_path = dummy
    ExtensionHelper.build_and_push_extensions()
    (manifest_path.parent / "dummy" / "workflow.json").write_text('{"changed": true}')

    ExtensionHelper.build_and_push_extensions()

    assert len(registry.pushed) == 1
    assert len(IssueTracker.issues) == 1
    assert "Increase the version" in IssueTracker.issues[0].msg


@pytest.mark.parametrize(
    "error",
    [
        OCIError("repository name not known to registry", code="NAME_UNKNOWN"),
        OCIError("HTTP 404"),
    ],
)
def test_pushes_when_the_registry_does_not_know_the_tag(registry, dummy, error):
    extension, _, _ = dummy
    registry.get_error = error

    ExtensionHelper.build_and_push_extensions()

    assert registry.pushed == [extension.tag]


def test_published_metadata_in_another_format_is_other_content(registry, dummy):
    extension, _, _ = dummy
    registry.tags[extension.tag] = {"files": ["not a file entry"]}

    ExtensionHelper.build_and_push_extensions()

    assert registry.pushed == []
    assert "Increase the version" in IssueTracker.issues[0].msg


@pytest.mark.parametrize(
    ("build_only", "status", "published"),
    [
        (False, Status.PUSHED, True),
        (False, Status.NOTHING_CHANGED, True),
        (False, Status.BUILT, False),
        (False, Status.BUILT_ONLY, False),
        (False, Status.NOT_BUILT, False),
        (False, Status.SKIPPED, False),
        (False, Status.FAILED, False),
        (True, Status.BUILT, True),
        (True, Status.BUILT_ONLY, True),
        (True, Status.NOTHING_CHANGED, True),
        (True, Status.PUSHED, True),
        (True, Status.NOT_BUILT, False),
        (True, Status.SKIPPED, False),
        (True, Status.FAILED, False),
    ],
)
def test_publishes_only_when_all_images_are_ready(build_config, registry, dummy, build_only, status, published):
    _, image, _ = dummy
    build_config.build_only = build_only
    image.status = status

    ExtensionHelper.build_and_push_extensions()

    assert bool(archives(build_config)) == published
    assert bool(registry.pushed) == (published and not build_only)
    assert len(IssueTracker.issues) == (0 if published else 1)


def test_build_only_packages_but_does_not_push(build_config, registry, dummy):
    build_config.build_only = True

    ExtensionHelper.build_and_push_extensions()

    assert archives(build_config) == ["dummy-extension-v0.1.0.tar.gz"]
    assert registry.clients == []


def test_microk8s_import_packages_but_does_not_push(build_config, registry, dummy):
    build_config.push_to_microk8s = True

    ExtensionHelper.build_and_push_extensions()

    assert archives(build_config) == ["dummy-extension-v0.1.0.tar.gz"]
    assert registry.clients == []


def test_rejected_push_without_credentials_is_a_warning(registry, dummy):
    registry.get_error = OCIError("authentication required", code="UNAUTHORIZED")

    with patch("build_cli.extension.extension_helper.logger") as logger:
        ExtensionHelper.build_and_push_extensions()

    assert IssueTracker.issues == []
    assert "extensionctl push" in logger.warning.call_args.args[0]


@pytest.mark.parametrize(
    "error",
    [
        OCIError("authentication required", code="UNAUTHORIZED"),
        OCIError("HTTP 500: internal error"),
        httpx.ConnectError("connection refused"),
    ],
)
def test_push_errors_with_credentials_are_issues(build_config, registry, dummy, error):
    build_config.registry_username = "user"
    build_config.registry_password = "secret"
    registry.get_error = error

    ExtensionHelper.build_and_push_extensions()

    assert registry.pushed == []
    assert len(IssueTracker.issues) == 1
