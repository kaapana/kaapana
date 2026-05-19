"""Client library for Kaapana OCI Extension Registry."""

import git
import io
import os
import re
import tarfile
import json
import tempfile
import uuid
import jsonschema
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from kaapana_containers.registries.registry import OCIRegistryDiscovery

# Parses: [git+]<URL>[@<ref>][#<subdir>]  (HTTPS and local paths only)
_SOURCE_RE = re.compile(
    r"^(?P<git>git\+)?"
    r"(?P<url>[^@#]+)"
    r"(?:@(?P<ref>[^#]+))?"
    r"(?:#(?P<subdir>.+))?$"
)


@dataclass
class SourceRef:
    """A parsed source reference for an extension.

    String format (inspired by pip VCS URLs)::

        /local/path
        git+<URL>
        git+<URL>@<ref>
        git+<URL>@<ref>#<subdir>
        git+<URL>#<subdir>

    URL may be HTTPS (``https://host/repo.git``) or SSH (``git@host:path``).

    Examples::

        SourceRef.parse("/path/to/my-extension")
        SourceRef.parse("git+https://example.com/repo.git@main#extensions/my-ext")
        SourceRef.parse("git+git@github.com:org/repo.git@v1.0#my-ext")
    """

    url: str
    is_git: bool
    ref: Optional[str] = None
    subdir: Optional[str] = None

    @classmethod
    def parse(cls, source: str) -> "SourceRef":
        m = _SOURCE_RE.match(source)
        if not m:
            raise ValueError(f"Invalid source reference: {source!r}")
        return cls(
            url=m.group("url"),
            is_git=bool(m.group("git")),
            ref=m.group("ref") or None,
            subdir=m.group("subdir") or None,
        )


class ExtensionUtilityLibrary:
    """Extension registry client.

    Wraps OCIRegistryDiscovery and adds extension-specific operations:
    build, push, pull, publish, validate.
    """

    API_VERSION = "v1"

    def __init__(
        self,
        registry: str = "",
        repo: str = "",
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self._manager = OCIRegistryDiscovery(
            registry_url=registry,
            repository=repo,
            username=username,
            password=password,
        )
        self.logger = self._manager.logger

    def list_tags(self) -> List[str]:
        """List all extension tags in the repository."""
        return self._manager.list_tags()

    def get(self, tag: str) -> Dict[str, Any]:
        """Return the extension manifest for a registry tag."""
        return self._manager.get(tag)

    def get_all_metadata(self, tag: Optional[str] = None) -> List[Tuple[str, Any]]:
        """Return extension_manifests for all tags, or a specific tag if given."""
        return self._manager.get_all_metadata(tag)

    def get_extension(self, tag: str) -> Dict[str, Any]:
        """Return the extension manifest for a registry tag."""
        return self._manager.get(tag)["user_metadata"]["extension_manifest"]

    def get_extensions(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return the extension manifests for a tag or for all tags."""
        if tag:
            return [self.get_extension(tag)]
        else:
            return [self.get_extension(t) for t in self.list_tags()]

    def delete_tag(self, tag: str) -> bool:
        """Delete an extension tag from the registry."""
        return self._manager.delete_tag(tag)

    def check_login(self) -> bool:
        """Return True if the current credentials are accepted by the registry."""
        try:
            resp = self._manager._request_with_auth_retry(
                "GET",
                f"{self._manager.registry_url}/v2/",
            )
            return resp.status_code < 400
        except Exception:
            return False

    @staticmethod
    def build(
        source: Union[str, "SourceRef", Path],
        output: Optional[Path] = None,
        recursive: bool = False,
    ) -> List[Tuple[str, Path]]:
        """Build extension(s) from a source, returning ``[(ext_source, archive), ...]``.

        Args:
            source: Local path, ``Path``, or ``git+URL[@ref][#subdir]``.
            output: Output directory for archives. Defaults to cwd for git sources,
                    or the extension directory's parent for local sources.
            recursive: Discover all extensions under source, not just the top-level one.
        """
        source_ref = SourceRef.parse(str(source))
        effective_output = (
            output if (output is not None or not source_ref.is_git) else Path.cwd()
        )
        ext_dir, clone_root, tmpdir = ExtensionUtilityLibrary._resolve_source(
            source_ref
        )
        try:
            extensions = ExtensionUtilityLibrary._find_extensions(
                ext_dir, clone_root, source_ref, recursive
            )
            return [
                (ext_source, ExtensionUtilityLibrary._build_dir(d, effective_output))
                for d, ext_source in extensions
            ]
        finally:
            if tmpdir:
                tmpdir.cleanup()

    def pull(self, tag: str, output_dir: Path = Path(".")) -> Path:
        """Pull an extension from the registry.

        Always saves the archive as <tag>.tar.gz in output_dir.

        Returns:
            Path to the saved archive.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        if not self._manager.download_files(tag, str(output_dir)):
            raise RuntimeError(f"Failed to download files for tag '{tag}'")

        metadata = self._manager.get(tag)
        ext_manifest = metadata.get("user_metadata", {}).get("extension_manifest", {})
        (output_dir / "extension_manifest.json").write_text(
            json.dumps(ext_manifest, indent=2)
        )
        return output_dir

    def push(
        self,
        ext_path: Path,
        bump: Optional[str] = None,
        overwrite: bool = False,
    ) -> str:
        """Push a .tar.gz extension archive to the registry.

        The tag is derived from the manifest ``id`` and ``version``.
        Using ``id`` rather than ``name`` avoids collisions between extensions
        from different authors that share the same name.

        Args:
            ext_path: Path to a .tar.gz archive produced by ``build``.
            bump: Auto-increment version: "major", "minor", or "patch".
            overwrite: Allow overwriting an existing tag.

        Returns:
            The registry tag the extension was pushed under.
        """
        if ext_path.is_dir():
            raise ValueError(
                "push expects a .tar.gz archive — use publish to build and push a directory"
            )

        with tempfile.TemporaryDirectory() as tmp:
            ext_dir = Path(tmp) / "ext"
            ext_dir.mkdir()

            try:
                with tarfile.open(ext_path, "r:gz") as tar:
                    if not tar.getmembers():
                        raise ValueError("Empty archive")
                    tar.extractall(ext_dir)
            except tarfile.ReadError:
                raise ValueError("Invalid or corrupt archive")

            ext_manifest_path = ext_dir / "extension_manifest.json"
            if not ext_manifest_path.exists():
                raise ValueError("Archive does not contain extension_manifest.json")

            ext_manifest = json.loads(ext_manifest_path.read_text())
            ext_name = ext_manifest.get("name")
            ext_id = ext_manifest.get("id")
            ext_version = str(ext_manifest.get("version"))
            if not ext_name or not ext_id or not ext_version:
                raise ValueError(
                    "extension_manifest.json must contain 'name', 'id', and 'version'"
                )

            self._validate_extension_files(ext_dir, ext_manifest)

            existing_tags = set(self._manager.list_tags())
            ext_tag = f"{ext_id}-v{ext_version}"

            if ext_tag in existing_tags and not bump and not overwrite:
                raise ValueError(
                    f"Tag '{ext_tag}' already exists — use overwrite=True to replace, "
                    "or --bump to auto-increment the version"
                )

            if bump:
                prefix = f"{ext_id}-v"
                matches = (
                    re.match(r"^(\d+)\.(\d+)\.(\d+)", t[len(prefix) :])
                    for t in existing_tags
                    if t.startswith(prefix)
                )
                existing_versions = [
                    (int(m.group(1)), int(m.group(2)), int(m.group(3)))
                    for m in matches
                    if m
                ]

                next_version = (
                    self.bump_version("{}.{}.{}".format(*max(existing_versions)), bump)
                    if existing_versions
                    else ext_version
                )
                ext_manifest["version"] = next_version
                ext_manifest_path.write_text(json.dumps(ext_manifest, indent=2) + "\n")
                ext_tag = f"{ext_id}-v{next_version}"

            relative_paths = []
            for content in ext_manifest.get("contents", []):
                content_name = content.get("name", "")
                for fe in content.get("files", []):
                    path = (
                        f"{content_name}/{fe['path']}" if content_name else fe["path"]
                    )
                    if not (ext_dir / path).is_file():
                        raise RuntimeError(f"File not found in archive: {path}")
                    relative_paths.append(path)

            user_metadata = {
                "extension_manifest": ext_manifest,
                "apiVersion": self.API_VERSION,
            }

            saved_dir = os.getcwd()
            os.chdir(ext_dir)
            try:
                success = self._manager.create_or_update_tag(
                    ext_tag, user_metadata, files=relative_paths
                )
            finally:
                os.chdir(saved_dir)

            if not success:
                raise RuntimeError("Registry push failed")

            self.logger.info(f"Pushed extension: {ext_tag}")
            return ext_tag

    def publish(
        self,
        source: Union[str, "SourceRef", Path],
        recursive: bool = False,
        bump: Optional[str] = None,
        overwrite: bool = False,
    ) -> List[Tuple[str, str]]:
        """Build and push extension(s), returning ``[(ext_source, ext_tag), ...]``.

        Args:
            source: Local path, ``Path``, or ``git+URL[@ref][#subdir]``.
            recursive: Publish all extensions found under source.
            bump: Auto-increment version: "major", "minor", or "patch".
            overwrite: Allow overwriting an existing tag.
        """
        with tempfile.TemporaryDirectory() as build_tmp:
            archives = ExtensionUtilityLibrary.build(source, Path(build_tmp), recursive)
            return [
                (ext_source, self.push(archive, bump=bump, overwrite=overwrite))
                for ext_source, archive in archives
            ]

    # ── Validation ────────────────────────────────────────────────────────────

    @staticmethod
    def validate(manifest_path: Path) -> Tuple[bool, List[str]]:
        """Validate an extension manifest file against the JSON schema."""
        try:
            manifest = json.loads(manifest_path.read_text())
        except Exception as e:
            return False, [f"Failed to read manifest: {e}"]

        schema_path = Path(__file__).parent / "schemas" / "extension_schema.json"
        try:
            schema = json.loads(schema_path.read_text())
        except Exception as e:
            return False, [f"Failed to load schema: {e}"]

        errors = []
        try:
            jsonschema.validate(instance=manifest, schema=schema)
        except jsonschema.ValidationError as ve:
            errors.append(
                f"Schema error at {'/'.join(map(str, ve.path))}: {ve.message}"
            )
        except jsonschema.SchemaError as se:
            errors.append(f"Invalid schema: {se}")

        return len(errors) == 0, errors

    def validate_extension(self, ext_dir: Path) -> Tuple[bool, List[str]]:
        """Validate an extension directory — schema plus file existence checks."""
        manifest_path = ext_dir / "extension_manifest.json"
        is_valid, errors = self.validate(manifest_path)
        if not is_valid:
            return False, errors

        try:
            manifest = json.loads(manifest_path.read_text())
        except Exception as e:
            return False, [f"Failed to read manifest: {e}"]

        try:
            self._validate_extension_files(ext_dir, manifest)
        except RuntimeError as e:
            errors.append(str(e))

        return len(errors) == 0, errors

    # ── Static utilities ──────────────────────────────────────────────────────

    @staticmethod
    def bump_version(version: str, bump_type: str = "patch") -> str:
        """Increment a semantic version string ("major", "minor", or "patch")."""
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)", version)
        if not m:
            raise ValueError(f"Invalid version format: {version!r}")
        major, minor, patch, suffix = (
            int(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
            m.group(4),
        )
        if bump_type == "major":
            return f"{major + 1}.0.0{suffix}"
        if bump_type == "minor":
            return f"{major}.{minor + 1}.0{suffix}"
        return f"{major}.{minor}.{patch + 1}{suffix}"

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _validate_extension_files(source_dir: Path, manifest: Dict[str, Any]) -> None:
        """Raise RuntimeError if any file referenced in manifest is missing."""
        for item in manifest.get("contents", []):
            content_name = item.get("name", "")
            if content_name and not (source_dir / content_name).is_dir():
                raise RuntimeError(
                    f"Content folder '{content_name}' not found in {source_dir}"
                )
            for fe in item.get("files", []):
                rel = (
                    f"{content_name}/{fe.get('path', '')}"
                    if content_name
                    else fe.get("path", "")
                )
                if not (source_dir / rel).is_file():
                    raise RuntimeError(f"File not found: {source_dir / rel}")

    @staticmethod
    def _resolve_source(
        source: "SourceRef",
    ) -> Tuple[Path, Path, Optional[tempfile.TemporaryDirectory]]:
        """Resolve a SourceRef to a local directory, cloning if necessary.

        Returns:
            (ext_dir, clone_root, tmpdir_or_None) — caller must call tmpdir.cleanup().
        """
        if not source.is_git:
            root = Path(source.url)
            ext_dir = root / source.subdir if source.subdir else root
            return ext_dir, root, None

        tmpdir = tempfile.TemporaryDirectory()
        clone_root = ExtensionUtilityLibrary._clone_from_git(
            source.url, source.ref, Path(tmpdir.name) / "cloned"
        )
        ext_dir = clone_root / source.subdir if source.subdir else clone_root
        return ext_dir, clone_root, tmpdir

    @staticmethod
    def _find_extensions(
        ext_dir: Path,
        clone_root: Path,
        source: "SourceRef",
        recursive: bool,
    ) -> List[Tuple[Path, str]]:
        """Return ``[(ext_dir, ext_source), ...]`` for all extensions under ext_dir."""
        if recursive:
            manifests = list(ext_dir.rglob("extension_manifest.json"))
            if not manifests:
                raise ValueError(f"No extensions found under {ext_dir}")
            return [
                (m.parent, f"{source.url} :: {m.parent.relative_to(clone_root)}")
                for m in manifests
            ]
        if not (ext_dir / "extension_manifest.json").exists():
            raise ValueError(
                f"No extension_manifest.json in {ext_dir}"
                " — use recursive=True to search subfolders"
            )
        return [(ext_dir, str(source.url))]

    @staticmethod
    def _build_dir(source_dir: Path, output: Optional[Path] = None) -> Path:
        """Build a .tar.gz archive from a single extension directory.

        Assigns a UUID ``id`` to the manifest if one is not already present.

        Returns:
            Path to the created archive (<name>-v<version>.tar.gz).
        """
        manifest_path = source_dir / "extension_manifest.json"
        if not manifest_path.is_file():
            raise RuntimeError(f"extension_manifest.json not found in {source_dir}")

        try:
            manifest = json.loads(manifest_path.read_text())
        except Exception as e:
            raise RuntimeError(f"Failed to read manifest: {e}")

        if "id" not in manifest:
            manifest["id"] = str(uuid.uuid4())
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

        ExtensionUtilityLibrary._validate_extension_files(source_dir, manifest)

        file_paths = []
        for item in manifest.get("contents", []):
            content_name = item.get("name", "")
            for fe in item.get("files", []):
                rel = (
                    f"{content_name}/{fe.get('path', '')}"
                    if content_name
                    else fe.get("path", "")
                )
                file_paths.append(source_dir / rel)

        output_dir = output if output is not None else source_dir.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        archive_path = (
            output_dir
            / f"{manifest.get('name', source_dir.name)}-v{manifest.get('version', '0.0.0')}.tar.gz"
        )
        tmp_path = archive_path.with_suffix(".tar.gz.tmp")

        try:
            manifest_bytes = json.dumps(manifest, indent=2).encode()
            with tarfile.open(tmp_path, "w:gz") as tar:
                info = tarfile.TarInfo(name="extension_manifest.json")
                info.size = len(manifest_bytes)
                tar.addfile(info, io.BytesIO(manifest_bytes))
                for p in file_paths:
                    tar.add(p, arcname=p.relative_to(source_dir))
            tmp_path.rename(archive_path)
        except:
            tmp_path.unlink(missing_ok=True)
            raise

        return archive_path

    @staticmethod
    def _clone_from_git(
        git_url: str, ref: Optional[str] = None, target_dir: Optional[Path] = None
    ) -> Path:
        """Clone a git repository and check out an optional ref."""
        if target_dir is None:
            target_dir = Path(tempfile.mkdtemp())

        try:
            repo = git.Repo.clone_from(git_url, str(target_dir))
        except git.GitCommandError as e:
            raise RuntimeError(f"Git clone failed: {e}")

        if not ref:
            return target_dir

        try:
            repo.git.checkout(ref)
        except git.GitCommandError:
            try:
                repo.remotes.origin.fetch(ref)
                repo.git.checkout("FETCH_HEAD")
            except git.GitCommandError as e:
                raise RuntimeError(f"Git checkout of '{ref}' failed: {e}")

        return target_dir
