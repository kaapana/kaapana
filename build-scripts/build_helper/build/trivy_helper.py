import json
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from alive_progress import alive_bar
from build_helper.build import BuildState, BuildConfig
from build_helper.container import Container
from build_helper.helm import HelmChart
from build_helper.utils import get_logger

logger = get_logger()


class TrivyHelper:
    _build_config: BuildConfig = None  # type: ignore
    _build_state: BuildState = None  # type: ignore
    _reports_path: Path = None  # type: ignore
    _cache_path: Path = None  # type: ignore

    @classmethod
    def init(cls, build_config: BuildConfig, build_state: BuildState) -> None:
        """Initialize Trivy helper with configuration and build state, setting up report and cache directories."""
        cls._build_config = build_config
        cls._build_state = build_state
        cls._reports_path = build_config.kaapana_dir / "security-reports"
        cls._reports_path.mkdir(parents=True, exist_ok=True)
        cls._cache_path = cls._reports_path / ".trivy_cache"
        cls._cache_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def misconfiguration_check(cls) -> None:
        """Run Trivy misconfiguration scans on selected charts and containers."""
        with alive_bar(
            len(cls._build_state.selected_charts),
            dual_line=True,
            title="Trivy misconfiguration chart scan",
        ) as bar:
            with ThreadPoolExecutor(max_workers=cls._build_config.parallel_processes) as executor:
                futures = {executor.submit(cls._check_chart, chart): chart for chart in cls._build_state.selected_charts}
                for future in as_completed(futures):
                    future.result()
                    bar()

        with alive_bar(
            len(cls._build_state.selected_containers),
            dual_line=True,
            title="Trivy misconfiguration container scan",
        ) as bar:
            with ThreadPoolExecutor(max_workers=cls._build_config.parallel_processes) as executor:
                futures = {executor.submit(cls._check_container, container): container for container in sorted(cls._build_state.selected_containers, key=lambda c: c.image_name)}
                for future in as_completed(futures):
                    future.result()
                    bar()

    @classmethod
    def _check_chart(cls, chart: HelmChart) -> None:
        """Run Trivy configuration scan for a single Helm chart."""
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
            f"{cls._cache_path}:/.cache",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            cls._build_config.trivy_image,
            "config",
            "--cache-dir",
            "/.cache",
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

    @classmethod
    def _check_container(cls, container: Container) -> None:
        """Run Trivy configuration scan for a single container."""
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
            f"{cls._cache_path}:/.cache",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            cls._build_config.trivy_image,
            "config",
            "--cache-dir",
            "/.cache",
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

    @classmethod
    def _docker_sock_gid(cls) -> int:
        return os.stat("/var/run/docker.sock").st_gid

    @classmethod
    def _ensure_db(cls) -> None:
        """Download/update the Trivy vulnerability DB once before parallel scans.
        Parallel workers all share the same cache dir, so concurrent DB updates
        deadlock on Trivy's file lock — pre-fetching avoids this."""
        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{cls._cache_path}:/.cache",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            cls._build_config.trivy_image,
            "image",
            "--cache-dir",
            "/.cache",
            "--download-db-only",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )

    @classmethod
    def _create_sbom(cls, container: Container, report_path: Path) -> tuple[Path, bool]:
        """Generate SBOM for a single container. Returns (report_path, skipped)."""
        filename = f"sbom_{container.image_name}.json"
        if (report_path / filename).exists():
            return report_path / filename, True
        # Each worker gets its own DB copy: bbolt acquires an exclusive lock on
        # the DB file even for reads, so sharing the cache across parallel workers
        # causes lock timeouts.
        worker_cache = Path(tempfile.mkdtemp(prefix=".trivy_worker_", dir=cls._reports_path))
        try:
            shutil.copytree(cls._cache_path, worker_cache, dirs_exist_ok=True)
            cmd = [
                "docker",
                "run",
                "--rm",
                # Docker socket needed for local-only images (never pushed to registry,
                # only accessible via the daemon). --group-add grants socket access
                # without running as root.
                "-v",
                "/var/run/docker.sock:/var/run/docker.sock",
                "-v",
                f"{worker_cache}:/.cache",
                "-v",
                f"{report_path}:/reports",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--group-add",
                str(cls._docker_sock_gid()),
                cls._build_config.trivy_image,
                "image",
                "--cache-dir",
                "/.cache",
                "--skip-db-update",
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
                raise subprocess.CalledProcessError(
                    result.returncode, cmd, output=result.stdout, stderr=result.stderr
                )
            return report_path / filename, False
        finally:
            shutil.rmtree(worker_cache, ignore_errors=True)

    @classmethod
    def create_sboms(cls) -> None:
        """Generate SBOMs for all selected containers."""
        report_path = cls._reports_path / "sboms"
        report_path.mkdir(parents=True, exist_ok=True)
        cls._ensure_db()
        with alive_bar(
            len(cls._build_state.selected_containers),
            dual_line=True,
            title="Trivy SBOM generation",
        ) as bar:
            with ThreadPoolExecutor(max_workers=cls._build_config.parallel_processes) as executor:
                futures = {executor.submit(cls._create_sbom, container, report_path): container for container in sorted(cls._build_state.selected_containers, key=lambda c: c.image_name)}
                for future in as_completed(futures):
                    path, skipped = future.result()
                    if skipped:
                        logger.info(f"SBOM already exists, skipping: {path.name}")
                    else:
                        logger.info(f"SBOM saved at {path.name}")
                    bar()

    @classmethod
    def _scan_container_vuln(cls, container: Container, report_path: Path) -> tuple[Path, bool]:
        """Run vulnerability scan for a single container. Returns (report_path, skipped)."""
        filename = f"vuln_report_{container.image_name}.json"
        if (report_path / filename).exists():
            return report_path / filename, True
        # Each worker gets its own DB copy: bbolt acquires an exclusive lock on
        # the DB file even for reads, so sharing the cache across parallel workers
        # causes lock timeouts.
        worker_cache = Path(tempfile.mkdtemp(prefix=".trivy_worker_", dir=cls._reports_path))
        try:
            shutil.copytree(cls._cache_path, worker_cache, dirs_exist_ok=True)
            cmd = [
                "docker",
                "run",
                "--rm",
                # Docker socket needed for local-only images (never pushed to registry,
                # only accessible via the daemon). --group-add grants socket access
                # without running as root.
                "-v",
                "/var/run/docker.sock:/var/run/docker.sock",
                "-v",
                f"{worker_cache}:/.cache",
                "-v",
                f"{report_path}:/reports",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--group-add",
                str(cls._docker_sock_gid()),
                cls._build_config.trivy_image,
                "image",
                "--cache-dir",
                "/.cache",
                "--skip-db-update",
                "--timeout",
                f"{cls._build_config.trivy_timeout}s",
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
                raise subprocess.CalledProcessError(
                    result.returncode, cmd, output=result.stdout, stderr=result.stderr
                )
            return report_path / filename, False
        finally:
            shutil.rmtree(worker_cache, ignore_errors=True)

    @classmethod
    def create_sboms(cls) -> None:
        """Generate SBOMs for all selected containers."""
        report_path = cls._reports_path / "sboms"
        report_path.mkdir(parents=True, exist_ok=True)
        cls._ensure_db()
        with alive_bar(
            len(cls._build_state.selected_containers),
            dual_line=True,
            title="Trivy SBOM generation",
        ) as bar:
            with ThreadPoolExecutor(max_workers=cls._build_config.parallel_processes) as executor:
                futures = {executor.submit(cls._create_sbom, container, report_path): container for container in sorted(cls._build_state.selected_containers, key=lambda c: c.image_name)}
                for future in as_completed(futures):
                    path, skipped = future.result()
                    if skipped:
                        logger.info(f"SBOM already exists, skipping: {path.name}")
                    else:
                        logger.info(f"SBOM saved at {path.name}")
                    bar()
        cls._consolidate_vuln_reports(report_path)
