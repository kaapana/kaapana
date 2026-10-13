from collections import defaultdict
from pathlib import Path

from build_cli.build import BuildConfig, BuildState, IssueTracker
from build_cli.container import Container
from build_cli.extension.extension import Extension, ExtensionManifestError
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

    @staticmethod
    def _extension_issue(name: str, path: Path, msg: str) -> None:
        IssueTracker.generate_issue(
            component=ExtensionHelper.__name__,
            name=name,
            msg=msg,
            level="ERROR",
            path=path,
        )
