import json
import os
import shutil
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

import kaapana_extensions
from fastapi import UploadFile
from jsonschema import Draft7Validator
from pydantic import ValidationError
from v1.services.oci.models import ExtensionManifest

UPLOAD_DIR = Path(os.environ.get("EXTENSION_UPLOAD_DIR", "/extensions/uploads"))
MAX_UPLOAD_BYTES = int(os.environ.get("EXTENSION_UPLOAD_MAX_BYTES", 100 * 1024 * 1024))
MAX_EXTRACTED_BYTES = int(os.environ.get("EXTENSION_UPLOAD_MAX_EXTRACTED_BYTES", 500 * 1024 * 1024))
MAX_ARCHIVE_ENTRIES = int(os.environ.get("EXTENSION_UPLOAD_MAX_ENTRIES", 10_000))
ARCHIVE_SUFFIX = ".tar.gz"
MANIFEST_FILE = "extension_manifest.json"
CHUNK_BYTES = 1024 * 1024
MANIFEST_SCHEMA = Path(kaapana_extensions.__file__).parent / "schemas" / "extension_schema.json"
MAX_TAG_LENGTH = 128
MAX_NAME_LENGTH = 255


class UploadTooLargeException(Exception):
    def __init__(self, max_bytes: int):
        super().__init__(f"The archive is larger than {max_bytes // (1024 * 1024)} MB.")


class InvalidArchiveException(Exception):
    pass


def extension_tag(manifest: ExtensionManifest) -> str:
    """Return the tag that extensionctl push would use for this manifest."""
    return f"{manifest.id}-v{manifest.version}"


def extension_dir(tag: str) -> Path:
    return UPLOAD_DIR / tag


def create_staging_dir() -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=".staging-", dir=UPLOAD_DIR))


async def receive_archive(file: UploadFile, staging_dir: Path) -> Path:
    """Stream the uploaded archive into the staging directory.

    :raises UploadTooLargeException: If the archive exceeds MAX_UPLOAD_BYTES.
    """
    archive = staging_dir / "extension.tar.gz"
    received = 0
    with open(archive, "wb") as f:
        while chunk := await file.read(CHUNK_BYTES):
            received += len(chunk)
            if received > MAX_UPLOAD_BYTES:
                raise UploadTooLargeException(MAX_UPLOAD_BYTES)
            f.write(chunk)
    return archive


def _check_members(tar: tarfile.TarFile) -> set[str]:
    """Reject archives that are not plain trees of files and return the file paths they contain."""
    members = tar.getmembers()
    if not members:
        raise InvalidArchiveException("The archive is empty.")
    if len(members) > MAX_ARCHIVE_ENTRIES:
        raise InvalidArchiveException(f"The archive has more than {MAX_ARCHIVE_ENTRIES} entries.")

    files = set()
    unpacked_bytes = 0
    for member in members:
        if member.issym() or member.islnk():
            raise InvalidArchiveException(f"The archive contains the link {member.name}. Links are not allowed.")
        if not (member.isfile() or member.isdir()):
            raise InvalidArchiveException(f"The archive entry {member.name} is neither a file nor a folder.")
        if member.isfile():
            files.add(str(PurePosixPath(member.name)))
            unpacked_bytes += member.size
    if unpacked_bytes > MAX_EXTRACTED_BYTES:
        raise InvalidArchiveException(f"The archive unpacks to more than {MAX_EXTRACTED_BYTES // (1024 * 1024)} MB.")
    return files


def _schema_errors(manifest_json: dict) -> list[str]:
    schema = json.loads(MANIFEST_SCHEMA.read_text())
    errors = sorted(Draft7Validator(schema).iter_errors(manifest_json), key=lambda error: list(error.path))
    return [f"{'/'.join(map(str, error.path)) or '(root)'}: {error.message}" for error in errors]


def _model_errors(error: ValidationError) -> list[str]:
    return [f"{'/'.join(map(str, detail['loc'])) or '(root)'}: {detail['msg']}" for detail in error.errors()]


def _is_relative_path(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return bool(parts) and not PurePosixPath(path).is_absolute() and ".." not in parts


def _check_contents(manifest: ExtensionManifest, archive_files: set[str]) -> None:
    if not manifest.contents:
        raise InvalidArchiveException("The extension manifest lists no contents.")

    tag = extension_tag(manifest)
    if len(tag) > MAX_TAG_LENGTH:
        raise InvalidArchiveException(f"The tag {tag} is longer than {MAX_TAG_LENGTH} characters.")

    listed_files = {MANIFEST_FILE}
    content_names = set()
    for content in manifest.contents:
        if content.name in content_names:
            raise InvalidArchiveException(f"The content name {content.name} is used more than once.")
        content_names.add(content.name)
        if not _is_relative_path(content.name) or len(PurePosixPath(content.name).parts) != 1:
            raise InvalidArchiveException(f"The content name {content.name!r} must be a single folder name.")
        for value, field in ((content.name, "content name"), (content.contentType, "content type")):
            if len(value) > MAX_NAME_LENGTH:
                raise InvalidArchiveException(f"The {field} {value} is longer than {MAX_NAME_LENGTH} characters.")
        for content_file in content.files:
            if not _is_relative_path(content_file.path):
                raise InvalidArchiveException(
                    f"The file path {content_file.path!r} of {content.name} must be relative and stay in its folder."
                )
            path = str(PurePosixPath(content.name, content_file.path))
            if path not in archive_files:
                raise InvalidArchiveException(f"The archive does not contain {path}.")
            listed_files.add(path)

    unlisted = sorted(archive_files - listed_files)
    if unlisted:
        raise InvalidArchiveException(
            f"The archive contains files that the manifest does not list: {', '.join(unlisted)}."
        )


def extract_archive(archive: Path, target_dir: Path) -> ExtensionManifest:
    """Extract an extensionctl archive and validate its manifest and files.

    :raises InvalidArchiveException: If the archive or its manifest is not a valid extension.
    """
    try:
        with tarfile.open(archive, "r:gz") as tar:
            archive_files = _check_members(tar)
            tar.extractall(target_dir, filter="data")
    except tarfile.FilterError as e:
        raise InvalidArchiveException(f"The archive contains a forbidden entry: {e}") from e
    except (tarfile.TarError, EOFError, OSError) as e:
        raise InvalidArchiveException(f"The file is not a valid .tar.gz archive: {e}") from e

    if MANIFEST_FILE not in archive_files:
        raise InvalidArchiveException(f"The archive does not contain {MANIFEST_FILE} at its top level.")

    try:
        manifest_json = json.loads((target_dir / MANIFEST_FILE).read_text())
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise InvalidArchiveException(f"{MANIFEST_FILE} is not valid JSON: {e}") from e
    if not isinstance(manifest_json, dict):
        raise InvalidArchiveException(f"{MANIFEST_FILE} must contain a JSON object.")

    errors = _schema_errors(manifest_json)
    if errors:
        raise InvalidArchiveException(f"The extension manifest is invalid: {'; '.join(errors)}")
    if not manifest_json.get("id"):
        raise InvalidArchiveException(
            "The extension manifest has no id. Build the archive with extensionctl build, which assigns one."
        )
    try:
        manifest = ExtensionManifest(**manifest_json)
    except ValidationError as e:
        raise InvalidArchiveException(f"The extension manifest is invalid: {'; '.join(_model_errors(e))}") from e

    _check_contents(manifest, archive_files)
    return manifest


def store_extension(source_dir: Path, tag: str) -> Path:
    """Move extracted files to the directory the install task reads from."""
    target = extension_dir(tag)
    shutil.rmtree(target, ignore_errors=True)
    shutil.move(source_dir, target)
    return target
