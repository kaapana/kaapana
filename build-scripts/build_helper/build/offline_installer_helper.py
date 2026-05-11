import json
import os
from pathlib import Path
from shutil import copy2, copyfile, copytree
from subprocess import PIPE, run
from time import sleep
from typing import Optional

from alive_progress import alive_bar
from build_helper.build import BuildState, BuildConfig, IssueTracker
from build_helper.container import ContainerHelper
from build_helper.utils import CommandUtils, get_logger

logger = get_logger()

RACOON_FILES_PATH_MAPPINGS = (
    ("vm-setup/vm-files/configure-vm.sh", "configure-vm.sh"),
    ("vm-setup/playbooks", "playbooks"),
    (
        "vm-setup/vm-files/template_node_config.yaml",
        "installation-scripts/template_node_config.yaml",
    ),
    ("kaapana/server-installation/pull_image.sh", "pull_image.sh"),
)


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
    def download_gpu_operator_chart(cls, target_path: Path) -> None:
        """Download and normalize the NVIDIA GPU Operator Helm chart."""
        logger.info("Downloading gpu-operator Helm chart...")
        target_path.mkdir(parents=True, exist_ok=True)

        chart_filename = "gpu-operator.tgz"
        cached_chart_path = target_path / chart_filename
        if cached_chart_path.exists():
            logger.info(f"Reusing cached GPU Operator chart: {cached_chart_path}")
            return

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
                return

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
        raise RuntimeError(error_msg)

    @classmethod
    def export_image_list_into_tarball(
        cls,
        image_list: list[str],
        images_tarball_path: Path,
        container_engine: str,
    ) -> None:
        """Export specified container images into a tarball using the given container engine."""
        logger.info(f"Exporting images to tarball: {images_tarball_path}")
        command = (
            [container_engine, "save"]
            + [i for i in image_list if not i.startswith("local-only")]
            + ["-o", str(images_tarball_path)]
        )
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

    @classmethod
    def package_directory_as_container(
        cls,
        package_dir: Path,
        image_name: str,
        image_tag: str,
        command: Optional[list[str]] = None,
    ) -> str:
        """Build a scratch image from a prepared directory and optionally push it."""
        dockerfile_path = package_dir / "Dockerfile"
        dockerignore_path = package_dir / ".dockerignore"
        previous_dockerfile = (
            dockerfile_path.read_text(encoding="utf-8")
            if dockerfile_path.exists()
            else None
        )
        previous_dockerignore = (
            dockerignore_path.read_text(encoding="utf-8")
            if dockerignore_path.exists()
            else None
        )

        image_ref = f"{cls._build_config.default_registry}/{image_name}:{image_tag}"
        build_command = command or [cls._build_config.container_engine, "build"]

        try:
            dockerfile_path.write_text(
                "\n".join(
                    [
                        "FROM scratch",
                        "COPY . /",
                        f'CMD ["echo","{image_name}"]',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            dockerignore_path.write_text(
                "Dockerfile\n.dockerignore\n",
                encoding="utf-8",
            )

            logger.info(f"Packaging offline installer as container image: {image_ref}")
            CommandUtils.run(
                [*build_command, "-t", image_ref, str(package_dir)],
                timeout=cls._build_config.save_image_timeout,
                logger=logger,
                context=f"build-{image_name}",
                exit_on_error=cls._build_config.exit_on_error,
                env=dict(
                    os.environ,
                    DOCKER_BUILDKIT=f"{cls._build_config.enable_build_kit}",
                ),
            )

            if cls._build_config.build_only:
                logger.info(f"Skipping push for offline installer image: {image_ref}")
                return image_ref

            CommandUtils.run(
                [cls._build_config.container_engine, "push", image_ref],
                timeout=cls._build_config.save_image_timeout,
                logger=logger,
                context=f"push-{image_name}",
                exit_on_error=cls._build_config.exit_on_error,
            )
            logger.info(f"Finished packaging offline installer image: {image_ref}")
            return image_ref
        finally:
            if previous_dockerfile is None:
                dockerfile_path.unlink(missing_ok=True)
            else:
                dockerfile_path.write_text(previous_dockerfile, encoding="utf-8")

            if previous_dockerignore is None:
                dockerignore_path.unlink(missing_ok=True)
            else:
                dockerignore_path.write_text(previous_dockerignore, encoding="utf-8")

    @classmethod
    def generate_microk8s_offline_version(
        cls,
        build_chart_dir: Path,
        package_version: Optional[str] = None,
    ) -> Optional[str]:
        """Assemble a complete Microk8s offline installer including snaps, Helm charts, and container images."""
        offline_dir = Path(cls._build_config.build_dir) / "microk8s-offline-installer"
        offline_dir.mkdir(parents=True, exist_ok=True)
        build_chart_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Generating Microk8s offline installer...")

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
        cls.download_gpu_operator_chart(offline_dir)
        if build_chart_dir != offline_dir:
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
                ContainerHelper.pull_container_image(image)
                bar()

        cls.export_image_list_into_tarball(
            microk8s_base_images,
            images_tarball_path,
            container_engine=cls._build_config.container_engine,
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

        logger.info("Finished generating Microk8s offline installer.")
        if not package_version:
            return None

        return cls.package_directory_as_container(
            package_dir=offline_dir,
            image_name="kaapana-server-kit",
            image_tag=package_version,
        )

    @classmethod
    def generate_racoon_files_version(
        cls,
        package_version: str,
    ) -> str:
        """Assemble and optionally push the racoon-files image used by offline installation."""
        package_dir = Path(cls._build_config.build_dir) / "racoon-files"
        package_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating racoon-files package in {package_dir}")
        racoon_root = Path(cls._build_config.kaapana_dir).parent

        for source_relative_path, target_relative_path in RACOON_FILES_PATH_MAPPINGS:
            source_path = racoon_root / source_relative_path
            target_path = package_dir / target_relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)

            if source_path.is_dir():
                copytree(source_path, target_path, dirs_exist_ok=True)
            else:
                copy2(source_path, target_path)

        return cls.package_directory_as_container(
            package_dir=package_dir,
            image_name="racoon-files",
            image_tag=package_version,
        )
