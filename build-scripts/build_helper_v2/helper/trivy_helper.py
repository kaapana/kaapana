import os
import subprocess
from enum import Enum, auto
from pathlib import Path

from alive_progress import alive_bar
from build_helper_v2.core.build_state import BuildState
from build_helper_v2.core.container import Container
from build_helper_v2.core.helm_chart import HelmChart
from build_helper_v2.models.build_config import BuildConfig
from build_helper_v2.utils.logger import get_logger

logger = get_logger()


class TrivyHelper:
    _build_config: BuildConfig = None  # type: ignore
    _build_state: BuildState = None  # type: ignore
    _reports_path: Path = None  # type: ignore
    _cache_path: Path = None  # type: ignore

    @classmethod
    def init(cls, build_config: BuildConfig, build_state: BuildState):
        cls._build_config = build_config
        cls._build_state = build_state
        cls._reports_path = build_config.kaapana_dir / "security-reports"
        cls._reports_path.mkdir(parents=True, exist_ok=True)
        cls._cache_path = cls._reports_path / ".trivy_cache"
        cls._cache_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def misconfiguration_check(cls):
        with alive_bar(
            len(cls._build_state.selected_charts),
            dual_line=True,
            title="Trivy misconfiguration chart scan",
        ) as bar:
            for chart in cls._build_state.selected_charts:
                bar.text(f"Checking chart: {chart.name}")
                cls._check_chart(chart)
                bar()

        with alive_bar(
            len(cls._build_state.selected_containers),
            dual_line=True,
            title="Trivy misconfiguration container scan",
        ) as bar:
            for container in cls._build_state.selected_containers:
                bar.text(f"Checking container: {container.image_name}")
                cls._check_container(container)
                bar()

    @classmethod
    def _check_chart(cls, chart: HelmChart):
        report_path = cls._reports_path / "charts"
        report_path.mkdir(parents=True, exist_ok=True)
        filename = f"misconfiguration_report_chart_{chart.name}.json"
        if (report_path / filename).exists():
            return
        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{chart.chartfile.parent}:/chart",
            "-v",
            f"{report_path}:/reports",
            "-v",
            f"{cls._cache_path}:/root/.cache",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            cls._build_config.trivy_image,
            "config",
            "--severity",
            ",".join(cls._build_config.configuration_check_severity_level),
            "/chart",
            "--format",
            "json",
            "--output",
            f"/reports/{filename}",
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=cls._build_config.trivy_timeout
        )
        if result.returncode != 0:
            logger.error(f"Trivy failed for {chart.name}:\n{result.stderr}")
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )
        logger.info(f"Chart misconfiguration report saved at {report_path / filename}")
        return result

    @classmethod
    def _check_container(cls, container: Container):
        report_path = cls._reports_path / "containers"
        report_path.mkdir(parents=True, exist_ok=True)
        filename = f"misconfiguration_report_container_{container.image_name}.json"
        if (report_path / filename).exists():
            return

        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{container.dockerfile.parent}:/container",
            "-v",
            f"{report_path}:/reports",
            "-v",
            f"{cls._cache_path}:/root/.cache",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            cls._build_config.trivy_image,
            "config",
            "--severity",
            ",".join(cls._build_config.configuration_check_severity_level),
            "/container",
            "--format",
            "json",
            "--output",
            f"/reports/{filename}",
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=cls._build_config.trivy_timeout
        )
        if result.returncode != 0:
            logger.error(f"Trivy failed for {container.tag}:\n{result.stderr}")
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )
        logger.info(
            f"Container misconfiguration report saved at {report_path / filename}"
        )
        return result

    @classmethod
    def create_sboms(cls):
        """Generate SBOMs for all selected containers."""
        report_path = cls._reports_path / "sboms"
        report_path.mkdir(parents=True, exist_ok=True)
        with alive_bar(
            len(cls._build_state.selected_containers),
            dual_line=True,
            title="Trivy SBOM generation",
        ) as bar:
            for container in cls._build_state.selected_containers:
                bar.text(f"Generating SBOM for: {container.image_name}")
                filename = f"sbom_{container.image_name}.json"

                if (report_path / filename).exists():
                    bar()
                    continue
                cmd = [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    "/var/run/docker.sock:/var/run/docker.sock",
                    "-v",
                    f"{cls._cache_path}:/.cache",
                    "-v",
                    f"{report_path}:/reports",
                    cls._build_config.trivy_image,
                    "image",
                    "--format",
                    "cyclonedx",
                    "--quiet",
                    "--timeout",
                    str(cls._build_config.trivy_timeout) + "s",
                    "--output",
                    f"/reports/{filename}",
                    container.tag,
                ]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=cls._build_config.trivy_timeout,
                )
                if result.returncode != 0:
                    logger.error(
                        f"Trivy SBOM generation failed for {container.tag}:\n{result.stderr}"
                    )
                    raise subprocess.CalledProcessError(
                        result.returncode,
                        cmd,
                        output=result.stdout,
                        stderr=result.stderr,
                    )
                logger.info(f"SBOM saved at {report_path}")
                bar()

    @classmethod
    def vulnerability_scan(cls):
        """Scan all selected containers for vulnerabilities."""
        report_path = cls._reports_path / "vuln_scan"
        report_path.mkdir(parents=True, exist_ok=True)
        with alive_bar(
            len(cls._build_state.selected_containers),
            dual_line=True,
            title="Trivy vulnerability scan",
        ) as bar:
            for container in cls._build_state.selected_containers:
                bar.text(f"Scanning container: {container.image_name}")

                filename = f"vuln_report_{container.image_name}.json"
                if (report_path / filename).exists():
                    bar()
                    continue
                cmd = [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    "/var/run/docker.sock:/var/run/docker.sock",
                    "-v",
                    f"{cls._cache_path}:/root/.cache",
                    "-v",
                    f"{report_path}:/reports",
                    cls._build_config.trivy_image,
                    "image",
                    "--severity",
                    ",".join(cls._build_config.vulnerability_severity_level),
                    "--scanners",
                    "vuln",
                    "--format",
                    "json",
                    "--output",
                    f"/reports/{filename}",
                    container.tag,
                ]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=cls._build_config.trivy_timeout,
                )
                if result.returncode != 0:
                    logger.error(
                        f"Trivy vulnerability scan failed for {container.tag}:\n{result.stderr}"
                    )
                    raise subprocess.CalledProcessError(
                        result.returncode,
                        cmd,
                        output=result.stdout,
                        stderr=result.stderr,
                    )
                logger.info(f"Vulnerability report saved at {report_path / filename}")
                bar()
