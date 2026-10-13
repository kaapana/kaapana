import json
import uuid
from pathlib import Path
from typing import Any

from build_cli.container import Container
from build_cli.helm.helm_chart import IMAGE_PATTERN

try:
    from kaapana_extensions.extensions import ExtensionUtilityLibrary
except ImportError as error:
    raise ImportError(
        "kaapana-build needs the extension libraries of this repository. "
        "Install them with: pip install -e lib/kaapana_containers -e lib/kaapana_extensions"
    ) from error

BUILD_VERSION_PLACEHOLDER = "{KAAPANA_BUILD_VERSION}"
# The extension manager can only install these content types.
SUPPORTED_CONTENT_TYPES = {"workflow-v1"}


class ExtensionManifestError(Exception):
    """An extension manifest that the extension manager would reject."""


def validate_manifest(manifest_path: Path) -> list[str]:
    """Return the reasons why the extension manager would reject the manifest.

    The library schema accepts manifests that the extension manager rejects, so its stricter rules are checked
    as well.
    """
    is_valid, errors = ExtensionUtilityLibrary().validate_extension(manifest_path.parent)
    if not is_valid:
        return errors

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = []
    if "id" not in manifest:
        # extensionctl would write a new random id into the source tree, and every build would publish a new tag.
        errors.append("The manifest has no id. Add a UUID as id and commit it.")
    else:
        try:
            uuid.UUID(str(manifest["id"]))
        except ValueError:
            errors.append(f"The id {manifest['id']!r} is not a UUID.")
    if not isinstance(manifest.get("dependencies"), list):
        errors.append("The manifest needs a list of dependencies, for example an empty list.")
    for content in manifest["contents"]:
        if content["contentType"] not in SUPPORTED_CONTENT_TYPES:
            errors.append(f"The content {content['name']!r} has the unsupported type {content['contentType']!r}.")
    return errors


def find_images(source_dir: Path, manifest: dict[str, Any]) -> tuple[set[str], set[str]]:
    """Return the images that the Python files of the extension use.

    The first set holds the names of images that are pulled in the platform version. The build builds these
    images. The second set holds images with a fixed version as ``name:version``.
    """
    image_names: set[str] = set()
    fixed_images: set[str] = set()
    for content in manifest["contents"]:
        for file_entry in content["files"]:
            path = source_dir / content["name"] / file_entry["path"]
            if path.suffix != ".py":
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                match = IMAGE_PATTERN.search(line)
                if not match:
                    continue
                if match.group("version") == BUILD_VERSION_PLACEHOLDER:
                    image_names.add(match.group("image_name"))
                else:
                    fixed_images.add(f"{match.group('image_name')}:{match.group('version')}")
    return image_names, fixed_images


class Extension:
    """A workflow extension in the repository, defined by its extension_manifest.json."""

    def __init__(
        self,
        manifest_path: Path,
        manifest: dict[str, Any],
        image_names: set[str],
        fixed_images: set[str],
    ):
        self.manifest_path = manifest_path
        self.manifest = manifest
        self.name: str = manifest["name"]
        self.id: str = str(manifest["id"])
        self.version: str = str(manifest["version"])
        self.image_names = image_names
        self.fixed_images = fixed_images

        self.containers: set[Container] = set()
        self.unresolved_images: set[str] = set()

    @classmethod
    def from_manifest(cls, manifest_path: Path) -> "Extension":
        errors = validate_manifest(manifest_path)
        if errors:
            raise ExtensionManifestError(" ".join(errors))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        image_names, fixed_images = find_images(manifest_path.parent, manifest)
        return cls(manifest_path, manifest, image_names, fixed_images)

    @property
    def source_dir(self) -> Path:
        return self.manifest_path.parent

    @property
    def tag(self) -> str:
        """The registry tag, as extensionctl derives it."""
        return f"{self.id}-v{self.version}"

    def __repr__(self) -> str:
        return f"Extension(name={self.name!r}, version={self.version!r}, id={self.id!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Extension):
            return False
        return self.manifest_path == other.manifest_path

    def __hash__(self) -> int:
        return hash(self.manifest_path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "id": self.id,
            "version": self.version,
            "tag": self.tag,
            "manifest_path": str(self.manifest_path),
            "containers": sorted(container.tag for container in self.containers),
            "unresolved_images": sorted(self.unresolved_images),
            "fixed_images": sorted(self.fixed_images),
        }
