import json
import platform
import sys
import tarfile
from pathlib import Path
from shutil import copyfile, copytree
from subprocess import PIPE, run
from time import sleep
from typing import Optional
from datetime import datetime, timezone

from alive_progress import alive_bar
from build_helper.build import BuildState, BuildConfig, IssueTracker
from build_helper.container import ContainerHelper
from build_helper.utils import get_logger

logger = get_logger()


class OfflineInstallerHelper:
    """
    Singleton-like helper class for generating offline installers.

    Responsibilities:
        - Download snap packages
        - Download Helm charts
        - Pull container images
        - Export container images as tarballs
        - Assemble Microk8s offline installer
    """

    _build_config: BuildConfig = None  # type: ignore
    _build_state: BuildState = None  # type: ignore

    @classmethod
    def init(cls, build_config: BuildConfig, build_state: BuildState) -> None:
        """Initialize the helper with build configuration and state."""
        if cls._build_config is None:
            cls._build_config = build_config
        if cls._build_state is None:
            cls._build_state = build_state

    @classmethod
    def download_snap_package(cls, name: str, version: str, target_path: Path) -> None:
        """Download and normalize a snap package to the specified directory."""
        logger.info(f"Downloading snap package: {name}")
        target_path.mkdir(parents=True, exist_ok=True)

        command = [
            "snap",
            "download",
            name,
            f"--target-directory={target_path}",
            f"--channel={version}",
        ]
        output = run(
            command,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=cls._build_config.snap_download_timeout,
        )
        if output.returncode != 0:
            logger.error(f"Snap download {name} failed: {output.stderr}")
            IssueTracker.generate_issue(
                component="Snap download",
                name=f"Snap download {name}",
                msg=f"Snap download failed {output.stderr}",
                level="ERROR",
            )
            return

        snap_filename = output.stdout.split("/")[-1].strip()
        snap_version = snap_filename.split("_")[-1].split(".")[0]
        snap_file_path = target_path / snap_filename
        assert snap_file_path.exists()
        snap_file_path.rename(
            snap_file_path.with_name(
                snap_file_path.name.replace(f"_{snap_version}", "")
            )
        )

        assert_file_path = target_path / f"{name}_{snap_version}.assert"
        assert assert_file_path.exists()
        assert_file_path.rename(
            assert_file_path.with_name(
                assert_file_path.name.replace(f"_{snap_version}", "")
            )
        )

    @classmethod
    def download_gpu_operator_chart(cls, target_path: Path) -> bool:
        """Download and normalize the NVIDIA GPU Operator Helm chart."""
        logger.info("Downloading gpu-operator Helm chart...")
        target_path.mkdir(parents=True, exist_ok=True)

        chart_filename = "gpu-operator.tgz"
        cached_chart_path = target_path / chart_filename
        if cached_chart_path.exists():
            logger.info(f"Reusing cached GPU Operator chart: {cached_chart_path}")
            return True

        helm_executable = cls._build_config.helm_executable or "helm"
        name = "nvidia/gpu-operator"
        version = "v25.3.0"
        versioned_chart_path = target_path / f"gpu-operator-{version}.tgz"
        retry_count = 3
        last_error: Optional[str] = None

        for attempt in range(1, retry_count + 1):
            for cmd in [
                [helm_executable, "repo", "add", "nvidia", "https://helm.ngc.nvidia.com/nvidia"],
                [helm_executable, "repo", "update"],
            ]:
                output = run(
                    cmd,
                    stdout=PIPE,
                    stderr=PIPE,
                    universal_newlines=True,
                    timeout=cls._build_config.helm_download_timeout,
                )
                if output.returncode != 0 and "already exists" not in output.stderr:
                    last_error = output.stderr.strip() or output.stdout.strip()
                    logger.warning(
                        f"Helm command failed on attempt {attempt}/{retry_count}: {last_error}"
                    )

            cmd = [
                helm_executable,
                "pull",
                name,
                f"--version={version}",
                f"--destination={target_path}",
            ]
            output = run(
                cmd,
                stdout=PIPE,
                stderr=PIPE,
                universal_newlines=True,
                timeout=cls._build_config.helm_download_timeout,
            )
            if output.returncode == 0 and versioned_chart_path.exists():
                versioned_chart_path.rename(cached_chart_path)
                return True

            last_error = output.stderr.strip() or output.stdout.strip()
            logger.warning(
                f"Helm download failed on attempt {attempt}/{retry_count}: {last_error}"
            )
            if attempt < retry_count:
                sleep(attempt * 2)

        error_msg = (
            f"Failed to download {name}:{version} after {retry_count} attempts. "
            f"Last Helm error: {last_error or 'unknown error'}. "
            f"Retry the build when https://helm.ngc.nvidia.com is available again, "
            f"or place {chart_filename} in {target_path} before rerunning the offline build."
        )
        logger.error(error_msg)
        IssueTracker.generate_issue(
            component="Helm",
            name="Helm download",
            msg=error_msg,
            level="ERROR",
        )
        if cls._build_config.exit_on_error:
            raise RuntimeError(error_msg)
        return False

    @classmethod
    def export_image_list_into_tarball(
        cls,
        image_list: list[str],
        images_tarball_path: Path,
        container_engine: str,
        image_platform: Optional[str] = None,
    ) -> None:
        """Export specified container images into a tarball using the given container engine."""
        logger.info(f"Exporting images to tarball: {images_tarball_path}")
        command = [container_engine, "save"]
        if image_platform:
            command += ["--platform", image_platform]
        command += ["-o", str(images_tarball_path)]
        command += [i for i in image_list if not i.startswith("local-only")]
        output = run(
            command,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=cls._build_config.save_image_timeout,
        )
        if output.returncode != 0:
            logger.error(f"Docker save failed: {output.stderr}")
            IssueTracker.generate_issue(
                component="docker save",
                name="Docker save",
                msg=f"Docker save failed {output.stderr}",
                level="ERROR",
            )

    @staticmethod
    def _default_image_platform() -> str:
        machine = platform.machine().lower()
        if machine in ("x86_64", "amd64"):
            return "linux/amd64"
        if machine in ("aarch64", "arm64"):
            return "linux/arm64"
        raise RuntimeError(f"Unsupported offline image architecture: {machine}")

    @classmethod
    def offline_image_platform(cls) -> str:
        return cls._build_config.offline_image_platform or cls._default_image_platform()

    @staticmethod
    def _offline_extra_target(offline_dir: Path, src: Path, dst: str) -> Path:
        dst_path = Path(dst or src.name)
        if dst_path.is_absolute():
            raise ValueError(f"Offline extra destination must be relative: {dst}")

        offline_root = offline_dir.resolve()
        target = (offline_root / dst_path).resolve()
        if not target.is_relative_to(offline_root):
            raise ValueError(f"Offline extra destination escapes installer root: {dst}")
        return target

    @classmethod
    def offline_dir(cls) -> Path:
        return Path(cls._build_config.build_dir) / "microk8s-offline-installer"

    @classmethod
    def handle_offline_installation(cls, platform_chart) -> None:
        offline_dir = cls.offline_dir()

        if cls._build_config.create_offline_installation:
            cls.generate_microk8s_offline_version(platform_chart.build_chart_dir)
            cls.export_platform_images_tarball(platform_chart)

        if cls._build_config.publish_offline_installer:
            if cls._build_config.build_only:
                logger.info("Skipping offline installer publish (--build-only).")
                return

            installer_ref = cls.publish_offline_installer(
                offline_dir=offline_dir,
                version=platform_chart.version,
            )
            if installer_ref:
                logger.info(
                    f"Finished: Published offline installer {installer_ref}."
                )

    @classmethod
    def export_platform_images_tarball(cls, platform_chart) -> None:
        if cls._build_config.no_images_tarball:
            logger.info("Skipping platform images tarball (--no-images-tarball).")
            return

        images_tarball_path = (
            platform_chart.build_chart_dir.parent
            / f"{platform_chart.name}-{platform_chart.version}-images.tar"
        )
        cls.export_image_list_into_tarball(
            image_list=[c.tag for c in cls._build_state.selected_containers],
            images_tarball_path=images_tarball_path,
            container_engine=cls._build_config.container_engine,
            image_platform=cls.offline_image_platform(),
        )
        logger.info("Finished: Generating platform images tarball.")

    @classmethod
    def generate_microk8s_offline_version(cls, build_chart_dir: Path) -> None:
        """Assemble a complete Microk8s offline installer including snaps, Helm charts, and container images."""
        offline_dir = cls.offline_dir()
        offline_dir.mkdir(parents=True, exist_ok=True)
        build_chart_dir.mkdir(parents=True, exist_ok=True)

        image_platform = cls.offline_image_platform()
        (offline_dir / "offline-image-platform").write_text(f"{image_platform}\n")
        logger.info(f"Generating Microk8s offline installer for {image_platform}...")

        # Download snap packages
        snaps = [
            ("core20", "latest/stable"),
            ("core24", "latest/stable"),
            ("microk8s", "1.33/stable"),
            ("snapd", "latest/stable"),
            ("helm", "latest/stable"),
        ]
        for name, version in snaps:
            cls.download_snap_package(name, version, offline_dir)

        # Download GPU Operator Helm chart
        gpu_chart_available = cls.download_gpu_operator_chart(offline_dir)
        if gpu_chart_available and build_chart_dir != offline_dir:
            copyfile(
                src=offline_dir / "gpu-operator.tgz",
                dst=build_chart_dir / "gpu-operator.tgz",
            )

        # Pull base images from JSON
        microk8s_images_json = (
            Path(cls._build_config.kaapana_dir)
            / "build-scripts"
            / "build_helper"
            / "configs"
            / "microk8s_images.json"
        )
        assert microk8s_images_json.exists()
        with microk8s_images_json.open(encoding="utf-8") as f:
            microk8s_base_images = json.load(f)["microk8s_base_images"]
        images_tarball_path = offline_dir / "microk8s_base_images.tar"
        logger.info("Pulling Microk8s base images...")
        with alive_bar(
            len(microk8s_base_images), dual_line=True, title="Pull Microk8s base-images"
        ) as bar:
            for image in microk8s_base_images:
                bar.text(f"Pull: {image}")
                ContainerHelper.pull_container_image(image, platform=image_platform)
                bar()

        cls.export_image_list_into_tarball(
            microk8s_base_images,
            images_tarball_path,
            container_engine=cls._build_config.container_engine,
            image_platform=image_platform,
        )

        # Copy kaapanactl.sh script
        copyfile(
            src=Path(cls._build_config.kaapana_dir, "kaapanactl.sh"),
            dst=Path(offline_dir, "kaapanactl.sh"),
        )
        # make it executable
        (Path(offline_dir, "kaapanactl.sh")).chmod(0o755)

        # Copy all .sh files in the cls._build_config.kaapana_dir, "utils" directory to offline_dir / utils
        utils_dir = Path(offline_dir, "utils")
        utils_dir.mkdir(parents=True, exist_ok=True)
        for sh_file in Path(cls._build_config.kaapana_dir, "utils").glob("*.sh"):
            copyfile(src=sh_file, dst=utils_dir / sh_file.name)
            # and make them executable
            (utils_dir / sh_file.name).chmod(0o755)

        # Include any caller-provided extra files/dirs in the offline installer tar.
        for entry in cls._build_config.offline_extra_files:
            src, _, dst = entry.partition(":")
            src = Path(src)
            try:
                target = cls._offline_extra_target(offline_dir, src, dst)
            except ValueError as exc:
                msg = str(exc)
                logger.error(msg)
                IssueTracker.generate_issue(
                    component="OfflineInstaller",
                    name="Offline extra file",
                    msg=msg,
                    level="ERROR",
                )
                if cls._build_config.exit_on_error:
                    raise RuntimeError(msg) from exc
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                copytree(src, target, dirs_exist_ok=True)
            elif src.is_file():
                copyfile(src, target)
            else:
                logger.warning(f"Offline extra path not found, skipping: {src}")

        logger.info("Finished generating Microk8s offline installer.")

    @classmethod
    def _oci_registry_cls(cls):
        """Import OCIRegistryDiscovery from the in-repo kaapana_containers lib (has dependency on python requests)."""
        try:
            from kaapana_containers.registries.registry import OCIRegistryDiscovery
        except ImportError:
            lib_root = Path(cls._build_config.kaapana_dir) / "lib" / "kaapana_containers"
            sys.path.insert(0, str(lib_root))
            from kaapana_containers.registries.registry import OCIRegistryDiscovery
        return OCIRegistryDiscovery

    @classmethod
    def publish_offline_installer(
        cls,
        offline_dir: Path,
        version: str,
        repository: str = "offline-installer",
    ) -> Optional[str]:
        """Tar the offline installer dir and publish it as <repo>:<version>."""
        if not offline_dir.is_dir():
            msg = (
                "Cannot publish offline installer: "
                f"{offline_dir} does not exist. Run with "
                "--create-offline-installation first."
            )
            logger.error(msg)
            IssueTracker.generate_issue(
                component="OfflineInstaller",
                name="Publish offline installer",
                msg=msg,
                level="ERROR",
            )
            if cls._build_config.exit_on_error:
                raise RuntimeError(msg)
            return None

        tarball = Path(cls._build_config.build_dir) / f"offline-installer-{version}.tar.gz"
        logger.info(f"Packaging offline installer {offline_dir} -> {tarball}")
        with tarfile.open(tarball, "w:gz") as tar:
            tar.add(offline_dir, arcname=".")  # unpacks straight into the target dir

        registry = cls._build_config.default_registry
        registry_host, _, repository_prefix = registry.partition("/")
        scheme = "http" if cls._build_config.plain_http else "https"
        url = (
            registry_host
            if "://" in registry_host
            else f"{scheme}://{registry_host}"
        )
        if repository_prefix:
            repository = f"{repository_prefix}/{repository}"

        client = cls._oci_registry_cls()(
            registry_url=url,
            repository=repository,
            username=cls._build_config.registry_username,
            password=cls._build_config.registry_password,
        )
        published = client.create_or_update_tag(
            tag=version,
            user_metadata={
                "kind": "kaapana-offline-installer",
                "kaapana_version": version,
                "built_at": datetime.now(timezone.utc).isoformat(),
            },
            files=[str(tarball)],
        )

        ref = f"{registry_host}/{repository}:{version}"
        if published:
            logger.info(f"Published offline installer to registry: {ref}")
            return ref

        msg = f"Failed to publish offline installer to {ref}"
        logger.error(msg)
        IssueTracker.generate_issue(
            component="OfflineInstaller",
            name="Publish offline installer",
            msg=msg,
            level="ERROR",
        )
        if cls._build_config.exit_on_error:
            raise RuntimeError(msg)
        return None
