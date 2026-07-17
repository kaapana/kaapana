import json
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from importlib.resources import files
from pathlib import Path

from alive_progress import alive_bar

from build_cli.build import BuildConfig, BuildState
from build_cli.container import Container
from build_cli.helm import HelmChart
from build_cli.utils import get_logger

logger = get_logger()


class TrivyHelper:
    _build_config: BuildConfig = None  # type: ignore
    _build_state: BuildState = None  # type: ignore
    _reports_path: Path = None  # type: ignore
    _cache_path: Path = None  # type: ignore

    @classmethod
    def init(cls, build_config: BuildConfig, build_state: BuildState) -> None:
        """Initialize Trivy helper with configuration and build state, setting up report and cache directories."""
        if shutil.which(build_config.trivy_executable) is None:
            logger.error(f"{build_config.trivy_executable} was not found!")
            logger.error(
                "-> install trivy: https://trivy.dev/latest/getting-started/installation/"
            )
            exit(1)
        cls._build_config = build_config
        cls._build_state = build_state
        cls._reports_path = build_config.kaapana_dir / "security-reports"
        cls._reports_path.mkdir(parents=True, exist_ok=True)
        cls._cache_path = cls._reports_path / ".trivy_cache"
        cls._cache_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _scan_targets(cls) -> list[Container]:
        """Containers to scan, sorted. In scan-only mode local-only images are
        skipped: they never reach the registry, and their layers are scanned as
        part of every derived image."""
        targets = sorted(
            cls._build_state.selected_containers, key=lambda c: c.image_name
        )
        if cls._build_config.scan_only:
            skipped = [c for c in targets if c.tag.startswith("local-only")]
            if skipped:
                logger.info(
                    f"Scan-only: skipping {len(skipped)} local-only base images "
                    "(layers are scanned within derived images)"
                )
            targets = [c for c in targets if not c.tag.startswith("local-only")]
        return targets

    @classmethod
    def misconfiguration_check(cls) -> None:
        """Run Trivy misconfiguration scans on selected charts and containers."""
        with alive_bar(
            len(cls._build_state.selected_charts),
            dual_line=True,
            title="Trivy misconfiguration chart scan",
        ) as bar:
            with ThreadPoolExecutor(
                max_workers=cls._build_config.parallel_processes
            ) as executor:
                futures = {
                    executor.submit(cls._check_chart, chart): chart
                    for chart in cls._build_state.selected_charts
                }
                for future in as_completed(futures):
                    future.result()
                    bar()

        with alive_bar(
            len(cls._build_state.selected_containers),
            dual_line=True,
            title="Trivy misconfiguration container scan",
        ) as bar:
            with ThreadPoolExecutor(
                max_workers=cls._build_config.parallel_processes
            ) as executor:
                futures = {
                    executor.submit(cls._check_container, container): container
                    for container in sorted(
                        cls._build_state.selected_containers, key=lambda c: c.image_name
                    )
                }
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
            cls._build_config.trivy_executable,
            "config",
            "--cache-dir",
            str(cls._cache_path),
            "--severity",
            ",".join(cls._build_config.configuration_check_severity_level),
            str(chart.chartfile.parent),
            "--format",
            "json",
            "--output",
            str(report_path / filename),
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
            cls._build_config.trivy_executable,
            "config",
            "--cache-dir",
            str(cls._cache_path),
            "--severity",
            ",".join(cls._build_config.configuration_check_severity_level),
            str(container.dockerfile.parent),
            "--format",
            "json",
            "--output",
            str(report_path / filename),
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
    def _ensure_db(cls) -> None:
        """Download/update the Trivy vulnerability DB once before parallel scans.
        Parallel workers all share the same cache dir, so concurrent DB updates
        deadlock on Trivy's file lock — pre-fetching avoids this."""
        cmd = [
            cls._build_config.trivy_executable,
            "image",
            "--cache-dir",
            str(cls._cache_path),
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
        worker_cache = Path(
            tempfile.mkdtemp(prefix=".trivy_worker_", dir=cls._reports_path)
        )
        try:
            shutil.copytree(cls._cache_path, worker_cache, dirs_exist_ok=True)
            # Trivy resolves the image via the local daemon first, then the
            # registry — daemon-less runners scan the pushed registry images.
            cmd = [
                cls._build_config.trivy_executable,
                "image",
                "--cache-dir",
                str(worker_cache),
                "--skip-db-update",
                "--format",
                "cyclonedx",
                "--quiet",
                "--timeout",
                str(cls._build_config.trivy_timeout) + "s",
                "--output",
                str(report_path / filename),
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
        targets = cls._scan_targets()
        with alive_bar(
            len(targets),
            dual_line=True,
            title="Trivy SBOM generation",
        ) as bar:
            with ThreadPoolExecutor(
                max_workers=cls._build_config.parallel_processes
            ) as executor:
                futures = {
                    executor.submit(cls._create_sbom, container, report_path): container
                    for container in targets
                }
                for future in as_completed(futures):
                    path, skipped = future.result()
                    if skipped:
                        logger.info(f"SBOM already exists, skipping: {path.name}")
                    else:
                        logger.info(f"SBOM saved at {path.name}")
                    bar()

    @classmethod
    def _scan_container_vuln(
        cls, container: Container, report_path: Path
    ) -> tuple[Path, bool]:
        """Run vulnerability scan for a single container. Returns (report_path, skipped)."""
        filename = f"vuln_report_{container.image_name}.json"
        if (report_path / filename).exists():
            return report_path / filename, True
        # Each worker gets its own DB copy: bbolt acquires an exclusive lock on
        # the DB file even for reads, so sharing the cache across parallel workers
        # causes lock timeouts.
        worker_cache = Path(
            tempfile.mkdtemp(prefix=".trivy_worker_", dir=cls._reports_path)
        )
        ignore_file = files("build_cli") / "configs" / ".trivyignore.yaml"
        has_ignore = ignore_file.is_file()
        ignore_flag = ["--ignorefile", str(ignore_file)] if has_ignore else []
        try:
            shutil.copytree(cls._cache_path, worker_cache, dirs_exist_ok=True)
            # Trivy resolves the image via the local daemon first, then the
            # registry — daemon-less runners scan the pushed registry images.
            cmd = [
                cls._build_config.trivy_executable,
                "image",
                "--cache-dir",
                str(worker_cache),
                "--skip-db-update",
                "--timeout",
                f"{cls._build_config.trivy_timeout}s",
                "--severity",
                ",".join(cls._build_config.vulnerability_severity_level),
                "--scanners",
                "vuln",
                *ignore_flag,
                "--format",
                "json",
                "--output",
                str(report_path / filename),
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
    def _consolidate_vuln_reports(cls, report_path: Path) -> Path:
        """Merge all per-container vuln_report_*.json files into one consolidated JSON.
        Deduplicates by CVE ID; collects container image names into Modules.
        Returns the path of the written file."""
        consolidated = {}
        for report_file in sorted(report_path.glob("vuln_report_*.json")):
            with open(report_file) as f:
                trivy_data = json.load(f)
            artifact_name = trivy_data.get(
                "ArtifactName"
            ) or report_file.stem.removeprefix("vuln_report_")
            for result in trivy_data.get("Results", []):
                for vuln in result.get("Vulnerabilities") or []:
                    cve_id = vuln["VulnerabilityID"]
                    if cve_id not in consolidated:
                        consolidated[cve_id] = {
                            "Title": vuln.get("Title", ""),
                            "PkgName": vuln.get("PkgName", ""),
                            "Severity": vuln.get("Severity", "UNKNOWN"),
                            "InstalledVersion": vuln.get("InstalledVersion", ""),
                            "FixedVersion": vuln.get("FixedVersion", ""),
                            "Modules": [],
                        }
                    if artifact_name not in consolidated[cve_id]["Modules"]:
                        consolidated[cve_id]["Modules"].append(artifact_name)

        output_path = cls._reports_path / "consolidated_vulnerability_report.json"
        with open(output_path, "w") as f:
            json.dump(consolidated, f, indent=2)
        logger.info(
            f"Consolidated vulnerability report saved at {output_path} ({len(consolidated)} unique CVEs)"
        )
        return output_path

    @classmethod
    def vulnerability_scan(cls) -> None:
        """Perform Trivy vulnerability scan on all selected containers with configured severity levels."""
        report_path = cls._reports_path / "vuln_scan"
        report_path.mkdir(parents=True, exist_ok=True)
        cls._ensure_db()
        targets = cls._scan_targets()
        with alive_bar(
            len(targets),
            dual_line=True,
            title="Trivy vulnerability scan",
        ) as bar:
            with ThreadPoolExecutor(
                max_workers=cls._build_config.parallel_processes
            ) as executor:
                futures = {
                    executor.submit(
                        cls._scan_container_vuln, container, report_path
                    ): container
                    for container in targets
                }
                for future in as_completed(futures):
                    container = futures[future]
                    try:
                        path, skipped = future.result()
                        if skipped:
                            logger.info(f"Skipping (exists): {path.name}")
                        else:
                            logger.info(f"Vulnerability report saved at {path.name}")
                    except subprocess.CalledProcessError as e:
                        logger.error(
                            f"Trivy vulnerability scan failed for {container.tag}:\n{e.stderr}"
                        )
                        raise
                    bar()
        cls._consolidate_vuln_reports(report_path)
