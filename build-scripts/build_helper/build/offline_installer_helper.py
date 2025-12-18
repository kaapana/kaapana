import json
import os
from pathlib import Path
from shutil import copyfile
from subprocess import PIPE, run

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
    def download_gpu_operator_chart(cls, target_path: Path) -> None:
        """Download and normalize the NVIDIA GPU Operator Helm chart."""
        logger.info("Downloading gpu-operator Helm chart...")
        target_path.mkdir(parents=True, exist_ok=True)

        for cmd in [
            ["helm", "repo", "add", "nvidia", "https://helm.ngc.nvidia.com/nvidia"],
            ["helm", "repo", "update"],
        ]:
            output = run(
                cmd,
                stdout=PIPE,
                stderr=PIPE,
                universal_newlines=True,
                timeout=cls._build_config.helm_download_timeout,
            )
            if output.returncode != 0 and "already exists" not in output.stderr:
                logger.error(f"Helm command failed: {output.stderr}")
                IssueTracker.generate_issue(
                    component="Helm",
                    name="Helm repo operation",
                    msg=f"{' '.join(cmd)} failed: {output.stderr}",
                    level="ERROR",
                )

        name = "nvidia/gpu-operator"
        version = "v25.3.0"
        cmd = [
            "helm",
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
        if output.returncode != 0:
            logger.error(f"Helm download failed: {output.stderr}")
            IssueTracker.generate_issue(
                component="Helm",
                name="Helm download",
                msg=f"Helm download {name} failed: {output.stderr}",
                level="ERROR",
            )
        else:
            helm_chart_path = target_path / f"gpu-operator-{version}.tgz"
            new_helm_chart_path = target_path / "gpu-operator.tgz"
            assert helm_chart_path.exists()
            helm_chart_path.rename(new_helm_chart_path)

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
    def generate_microk8s_offline_version(cls, build_chart_dir: Path) -> None:
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
        cls.download_gpu_operator_chart(build_chart_dir)

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

        logger.info("Finished generating Microk8s offline installer.")
