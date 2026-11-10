import asyncio
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx
from kaapana_containers.registries.registry import OCIError

from build_cli.build import BuildConfig, BuildState, IssueTracker
from build_cli.container import Container, Status
from build_cli.extension.extension import Extension, ExtensionManifestError, ExtensionUtilityLibrary
from build_cli.utils import get_logger, git_ignored, should_ignore_path

logger = get_logger()

# Only the workflows in this directory belong to the platform. Manifests elsewhere, for example test data, do not.
EXTENSIONS_DIR = "data-processing/workflows"
MANIFEST_NAME = "extension_manifest.json"


class ExtensionHelper:
    _build_config: BuildConfig = None  # type: ignore
    _build_state: BuildState = None  # type: ignore

    @classmethod
    def init(cls, build_config: BuildConfig, build_state: BuildState):
        if cls._build_config is None:
            cls._build_config = build_config
        if cls._build_state is None:
            cls._build_state = build_state

    @classmethod
    def collect_extensions(cls) -> set[Extension]:
        """Find and validate the extension manifests in the workflows directory."""
        extensions_dir = cls._build_config.kaapana_dir / EXTENSIONS_DIR
        manifests = sorted(extensions_dir.rglob(MANIFEST_NAME))
        ignored = git_ignored(set(manifests), repo_dir=cls._build_config.kaapana_dir)
        manifests = [
            manifest
            for manifest in manifests
            if manifest not in ignored and not should_ignore_path(manifest, cls._build_config.build_ignore_patterns)
        ]
        logger.info("")
        logger.info(f"-> Found {len(manifests)} extensions @{EXTENSIONS_DIR}")

        extensions: list[Extension] = []
        for manifest in manifests:
            try:
                extensions.append(Extension.from_manifest(manifest))
            except ExtensionManifestError as error:
                cls._extension_issue(name=manifest.parent.name, path=manifest, msg=str(error))

        # The registry tag is derived from the id, and the archive name from the name and the version.
        # Duplicates would overwrite each other, and it is unclear which one is meant, so all of them are rejected.
        groups: dict[object, list[Extension]] = defaultdict(list)
        for extension in extensions:
            groups[extension.id].append(extension)
            groups[(extension.name, extension.version)].append(extension)

        for extension in extensions:
            others = {
                str(other.manifest_path)
                for key in (extension.id, (extension.name, extension.version))
                for other in groups[key]
                if other is not extension
            }
            if others:
                cls._extension_issue(
                    name=extension.name,
                    path=extension.manifest_path,
                    msg=f"The id, or the name and version, are also used by {', '.join(sorted(others))}.",
                )
                continue

            if extension.fixed_images:
                logger.warning(
                    f"{extension.name}: images with a fixed version are not built: {sorted(extension.fixed_images)}"
                )
            if not extension.image_names:
                logger.warning(f"{extension.name}: no image with the version {{KAAPANA_BUILD_VERSION}} was found")
            cls._build_state.extensions_available.add(extension)

        return cls._build_state.extensions_available

    @classmethod
    def resolve_extension_containers(cls) -> None:
        """Link each extension to the containers of its images."""
        # With --lint-only, no containers are collected, so there is nothing to look up.
        if cls._build_config.lint_only:
            return

        for extension in cls._build_state.extensions_available:
            for image_name in sorted(extension.image_names):
                matches = [
                    container
                    for container in cls._build_state.containers_available
                    if container.image_name == image_name and container.registry == cls._build_config.default_registry
                ]
                if len(matches) == 1:
                    extension.containers.add(matches[0])
                    continue
                extension.unresolved_images.add(image_name)
                cls._extension_issue(
                    name=extension.name,
                    path=extension.manifest_path,
                    msg=f"Expected one container for the image {image_name}, found {len(matches)}.",
                )

    @classmethod
    def select_extensions(cls, selected_containers: set[Container], explicit_selection: bool) -> None:
        """Select the extensions whose images are all part of this build.

        A build must never publish an extension whose images it did not try to build.
        """
        selected = set()
        for extension in cls._build_state.extensions_available:
            if extension.unresolved_images:
                continue
            if not extension.containers:
                # Without images, nothing ties the extension to a partial build.
                if not explicit_selection:
                    selected.add(extension)
                continue
            if extension.containers <= selected_containers:
                selected.add(extension)
        cls._build_state.selected_extensions = selected

    @classmethod
    def build_and_push_extensions(cls) -> None:
        """Package the selected extensions and push them to the extensions repository of the default registry."""
        extensions = sorted(cls._build_state.selected_extensions, key=lambda e: (e.name, e.version))
        if not extensions:
            return
        logger.info("")
        logger.info(f"-> Packaging {len(extensions)} extensions")

        archives: list[tuple[Extension, Path]] = []
        for extension in extensions:
            not_ready = sorted(c.tag for c in extension.containers if c.status not in cls._ready_states())
            if not_ready:
                cls._extension_issue(
                    name=extension.name,
                    path=extension.manifest_path,
                    msg=f"The extension is not published, because these images are not ready: {', '.join(not_ready)}.",
                )
                continue
            try:
                ((_, archive),) = ExtensionUtilityLibrary.build(
                    extension.source_dir, output=cls._build_config.build_dir / "extensions"
                )
            except (ValueError, RuntimeError, OSError) as error:
                cls._extension_issue(name=extension.name, path=extension.manifest_path, msg=str(error))
                continue
            logger.info(f"{extension.name}:{extension.version}: packaged to {archive}")
            archives.append((extension, archive))

        if cls._build_config.build_only:
            logger.info("Build-only: the extensions are packaged, but not pushed.")
            return
        if cls._build_config.push_to_microk8s:
            logger.info("The images were imported into microk8s and not pushed, so the extensions are not pushed.")
            return
        if archives:
            asyncio.run(cls._push_extensions(archives))

    @classmethod
    def registry_location(cls) -> tuple[str, str]:
        """Return the registry URL and the repository for the extensions, derived from the default registry."""
        registry = cls._build_config.default_registry.rstrip("/")
        scheme = "http" if cls._build_config.plain_http else "https"
        if "://" in registry:
            scheme, registry = registry.split("://", 1)
        host, _, prefix = registry.partition("/")
        repository = f"{prefix}/extensions" if prefix else "extensions"
        return f"{scheme}://{host}", repository

    @classmethod
    def _ready_states(cls) -> set[Status]:
        # After the container push, an image is PUSHED, or NOTHING_CHANGED if its immutable tag already exists.
        # Images that an aborted build never processed stay NOT_BUILT.
        # A worker that crashes between build and push can leave NOTHING_CHANGED behind without a push.
        # The container states cannot tell this case apart.
        states = {Status.PUSHED, Status.NOTHING_CHANGED}
        if cls._build_config.build_only:
            states |= {Status.BUILT, Status.BUILT_ONLY}
        return states

    @classmethod
    async def _push_extensions(cls, archives: list[tuple[Extension, Path]]) -> None:
        url, repository = cls.registry_location()
        username = cls._build_config.registry_username or ""
        password = cls._build_config.registry_password or ""
        anonymous = not (username and password)

        async with ExtensionUtilityLibrary(url, repository, username, password) as client:
            for extension, archive in archives:
                try:
                    await cls._push_extension(client, extension, archive)
                except (OCIError, httpx.HTTPError, httpx.InvalidURL, ValueError, RuntimeError, OSError) as error:
                    # Without credentials, the user may rely on a docker login, which the OCI client cannot use.
                    if anonymous and cls._is_auth_error(error):
                        logger.warning(
                            f"{extension.name}: the registry rejected the push without credentials ({error}). "
                            f"Push it by hand: extensionctl push {archive} --registry {url} --repo {repository} "
                            "--user <user> --password <password>"
                        )
                        continue
                    cls._extension_issue(
                        name=extension.name,
                        path=extension.manifest_path,
                        msg=f"The extension could not be pushed to {url}/{repository}: {error}",
                    )

    @classmethod
    async def _push_extension(cls, client: ExtensionUtilityLibrary, extension: Extension, archive: Path) -> None:
        # The tag is read directly, because a tag list can be split into pages.
        try:
            published = await client.get(extension.tag)
        except OCIError as error:
            if not cls._is_not_found(error):
                raise
            published = None

        if published is not None:
            # The build never changes a published version, but rebuilding the same content is fine.
            if cls._has_same_content(extension, published):
                logger.info(f"{extension.name}:{extension.version}: already published as {extension.tag}")
                return
            cls._extension_issue(
                name=extension.name,
                path=extension.manifest_path,
                msg=f"The registry already has {extension.tag} with other content. Increase the version in the manifest.",
            )
            return

        await client.push(archive)
        logger.info(f"{extension.name}:{extension.version}: pushed as {extension.tag}")

    @staticmethod
    def _has_same_content(extension: Extension, published: dict[str, Any]) -> bool:
        local_files = {}
        for content in extension.manifest["contents"]:
            for file_entry in content["files"]:
                path = f"{content['name']}/{file_entry['path']}" if content["name"] else file_entry["path"]
                digest = hashlib.sha256((extension.source_dir / path).read_bytes()).hexdigest()
                local_files[path] = f"sha256:{digest}"
        try:
            published_files = {entry["filename"]: entry["digest"] for entry in published.get("files", [])}
            published_manifest = published.get("user_metadata", {}).get("extension_manifest")
        except (AttributeError, KeyError, TypeError):
            # Metadata in another format cannot be the same content.
            return False
        return published_manifest == extension.manifest and published_files == local_files

    @staticmethod
    def _is_not_found(error: OCIError) -> bool:
        # A missing tag, or a repository that the first push creates.
        return error.code in {"MANIFEST_UNKNOWN", "NAME_UNKNOWN"} or str(error).startswith("HTTP 404")

    @staticmethod
    def _is_auth_error(error: Exception) -> bool:
        if isinstance(error, OCIError):
            return error.code in {"UNAUTHORIZED", "DENIED"} or str(error).startswith(("HTTP 401", "HTTP 403"))
        return False

    @staticmethod
    def _extension_issue(name: str, path: Path, msg: str) -> None:
        IssueTracker.generate_issue(
            component=ExtensionHelper.__name__,
            name=name,
            msg=msg,
            level="ERROR",
            path=path,
        )
