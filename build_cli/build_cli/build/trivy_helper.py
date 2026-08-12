import json
import shutil
import subprocess
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from importlib.resources import files
from pathlib import Path

from alive_progress import alive_bar

from build_cli.build import BuildConfig, BuildState
from build_cli.build.offline_installer_helper import OFFLINE_SNAP_PACKAGES
from build_cli.container import Container
from build_cli.helm import HelmChart
from build_cli.utils import get_logger

logger = get_logger()


class ContainerScanner:
    _build_config: BuildConfig = None  # type: ignore
    _build_state: BuildState = None  # type: ignore
    _reports_path: Path = None  # type: ignore
    _cache_path: Path = None  # type: ignore

    @classmethod
    def init(cls, build_config: BuildConfig, build_state: BuildState) -> None:
        """Initialize Trivy helper with configuration and build state, setting up report and cache directories."""
        trivy_exec = getattr(build_config, "trivy_executable", "trivy")
        if shutil.which(trivy_exec) is None:
            logger.error(f"{trivy_exec} was not found!")
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
    def _fail_on_scan_errors(
        cls, action: str, failures: list[tuple[Container, str]]
    ) -> None:
        """Raise once, after every container has had its chance to scan, summarizing
        every image that couldn't be pulled/scanned — most commonly a tag not present
        in the registry. Reports already written for the other containers are left in
        place; this only makes sure the gap isn't silent."""
        if not failures:
            return
        summary = "\n".join(f"  - {container.tag}" for container, _ in failures)
        raise RuntimeError(
            f"{action} failed for {len(failures)} image(s) — most likely not present "
            f"in the registry:\n{summary}"
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
        """Generate SBOMs for all selected containers. Images that can't be
        pulled (e.g. not present in the registry) are logged and skipped so
        the rest still get an SBOM; if any failed, fails at the end so the
        gap isn't silent."""
        report_path = cls._reports_path / "sboms"
        report_path.mkdir(parents=True, exist_ok=True)
        cls._ensure_db()
        targets = cls._scan_targets()
        failures: list[tuple[Container, str]] = []
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
                    container = futures[future]
                    try:
                        path, skipped = future.result()
                    except subprocess.CalledProcessError as e:
                        logger.error(f"SBOM generation failed for {container.tag}:\n{e.stderr}")
                        failures.append((container, e.stderr))
                    else:
                        if skipped:
                            logger.info(f"SBOM already exists, skipping: {path.name}")
                        else:
                            logger.info(f"SBOM saved at {path.name}")
                    bar()
        cls._fail_on_scan_errors("SBOM generation", failures)

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
    def vulnerability_scan(cls) -> None:
        """Perform Trivy vulnerability scan on all selected containers with configured severity levels.
        Images that can't be pulled (e.g. not present in the registry) are logged and skipped so the
        rest still get scanned; if any failed, fails at the end so the gap isn't silent."""
        report_path = cls._reports_path / "vuln_scan"
        report_path.mkdir(parents=True, exist_ok=True)
        cls._ensure_db()
        targets = cls._scan_targets()
        failures: list[tuple[Container, str]] = []
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
                    except subprocess.CalledProcessError as e:
                        logger.error(
                            f"Trivy vulnerability scan failed for {container.tag}:\n{e.stderr}"
                        )
                        failures.append((container, e.stderr))
                    else:
                        if skipped:
                            logger.info(f"Skipping (exists): {path.name}")
                        else:
                            logger.info(f"Vulnerability report saved at {path.name}")
                    bar()
        cls._fail_on_scan_errors("Vulnerability scan", failures)


class OfflinePackagesScanner:
    """Vulnerability scanning for packages the offline installer bundles directly
    (currently: raw .snap files — see OFFLINE_SNAP_PACKAGES) that never pass through
    a container build and so are invisible to ContainerScanner. `trivy fs` can't
    analyze the Go binaries inside snaps, so scanning is delegated to
    ci/ci-code/clean/trivy_scan_anything.sh, which packs each snap into a scratch
    docker image and runs `trivy image` against that."""

    _build_config: BuildConfig = None  # type: ignore
    _build_state: BuildState = None  # type: ignore
    _reports_path: Path = None  # type: ignore

    @classmethod
    def init(cls, build_config: BuildConfig, build_state: BuildState) -> None:
        """Initialize with configuration and build state, setting up the report directory."""
        cls._build_config = build_config
        cls._build_state = build_state
        cls._reports_path = build_config.kaapana_dir / "security-reports" / "snap_scans"
        cls._reports_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _scan_script(cls) -> Path:
        return (
            cls._build_config.kaapana_dir
            / "ci"
            / "ci-code"
            / "clean"
            / "trivy_scan_anything.sh"
        )

    @classmethod
    def _scan_snap(cls, name: str, channel: str) -> tuple[Path, bool]:
        """Scan a single snap package. Returns (report_path, skipped)."""
        report_path = cls._reports_path / f"{name}.json"
        if report_path.exists():
            return report_path, True
        cmd = [
            "bash",
            str(cls._scan_script()),
            "--severity",
            ",".join(cls._build_config.vulnerability_severity_level),
            "--format",
            "json",
            "snap",
            name,
            channel,
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=cls._build_config.trivy_timeout
        )
        (cls._reports_path / f"{name}.log").write_text(result.stderr)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )
        report_path.write_text(result.stdout)
        return report_path, False

    @classmethod
    def vulnerability_scan(cls) -> None:
        """Scan every offline-installer snap package for vulnerabilities. Snap-store
        reachability and nested docker-in-docker are newer, less-proven dependencies
        than the container scan path, so failures here are logged and skipped —
        never raised — matching the tool's existing best-effort/non-fatal contract
        for snap scanning."""
        with alive_bar(
            len(OFFLINE_SNAP_PACKAGES),
            dual_line=True,
            title="Snap package vulnerability scan",
        ) as bar:
            with ThreadPoolExecutor(
                max_workers=cls._build_config.parallel_processes
            ) as executor:
                futures = {
                    executor.submit(cls._scan_snap, name, channel): name
                    for name, channel in OFFLINE_SNAP_PACKAGES
                }
                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        path, skipped = future.result()
                    except subprocess.CalledProcessError as e:
                        logger.warning(
                            f"Snap vulnerability scan failed for {name} (non-fatal):\n{e.stderr}"
                        )
                    else:
                        if skipped:
                            logger.info(f"Skipping (exists): {path.name}")
                        else:
                            logger.info(f"Snap vulnerability report saved at {path.name}")
                    bar()


def _load_json_report(report_file: Path) -> dict | None:
    """Load a Trivy/CycloneDX JSON report, or None if it's missing/malformed.
    Scan reports feeding consolidation may come from best-effort scanners
    (OfflinePackagesScanner) — a single bad file shouldn't take the whole
    consolidated report down."""
    try:
        with open(report_file) as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.warning(f"Skipping unparseable scan report: {report_file}")
        return None


def consolidate_vulnerability_reports(reports_path: Path) -> Path:
    """Merge every per-container (vuln_scan/vuln_report_*.json) and per-snap
    (snap_scans/*.json) Trivy report under `reports_path` into one CVE-keyed JSON.
    Deduplicates by CVE ID; each CVE lists every artifact it was found in, tagged
    by type (container/snap) so a dashboard can tell them apart. Returns the path
    of the written file."""
    consolidated: dict[str, dict] = {}

    def _merge(trivy_data: dict, artifact_type: str, artifact_name: str) -> None:
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
                        "Artifacts": [],
                    }
                artifact = {"name": artifact_name, "type": artifact_type}
                if artifact not in consolidated[cve_id]["Artifacts"]:
                    consolidated[cve_id]["Artifacts"].append(artifact)

    for report_file in sorted((reports_path / "vuln_scan").glob("vuln_report_*.json")):
        trivy_data = _load_json_report(report_file)
        if trivy_data is None:
            continue
        artifact_name = trivy_data.get(
            "ArtifactName"
        ) or report_file.stem.removeprefix("vuln_report_")
        _merge(trivy_data, "container", artifact_name)

    for report_file in sorted((reports_path / "snap_scans").glob("*.json")):
        trivy_data = _load_json_report(report_file)
        if trivy_data is None:
            continue
        _merge(trivy_data, "snap", report_file.stem)

    output_path = reports_path / "consolidated_vulnerability_report.json"
    with open(output_path, "w") as f:
        json.dump(consolidated, f, indent=2)
    logger.info(
        f"Consolidated vulnerability report saved at {output_path} ({len(consolidated)} unique CVEs)"
    )
    return output_path


def consolidate_misconfiguration_reports(reports_path: Path) -> Path:
    """Merge every chart (charts/misconfiguration_report_chart_*.json) and container
    (containers/misconfiguration_report_container_*.json) Trivy config-scan report
    under `reports_path` into one rule-ID-keyed JSON. Deduplicates by misconfiguration
    ID (e.g. DS-0002, KSV-0001); each entry lists every chart/container that failed
    it. Returns the path of the written file."""
    consolidated: dict[str, dict] = {}

    def _merge(trivy_data: dict, artifact_type: str, artifact_name: str) -> None:
        for result in trivy_data.get("Results", []):
            for m in result.get("Misconfigurations") or []:
                if m.get("Status") not in (None, "FAIL"):
                    continue
                rule_id = m.get("ID")
                if not rule_id:
                    continue
                if rule_id not in consolidated:
                    consolidated[rule_id] = {
                        "Title": m.get("Title", ""),
                        "Severity": m.get("Severity", "UNKNOWN"),
                        "Message": m.get("Message", ""),
                        "Resolution": m.get("Resolution", ""),
                        "PrimaryURL": m.get("PrimaryURL", ""),
                        "Artifacts": [],
                    }
                artifact = {"name": artifact_name, "type": artifact_type}
                if artifact not in consolidated[rule_id]["Artifacts"]:
                    consolidated[rule_id]["Artifacts"].append(artifact)

    for report_file in sorted(
        (reports_path / "charts").glob("misconfiguration_report_chart_*.json")
    ):
        trivy_data = _load_json_report(report_file)
        if trivy_data is None:
            continue
        name = report_file.stem.removeprefix("misconfiguration_report_chart_")
        _merge(trivy_data, "chart", name)

    for report_file in sorted(
        (reports_path / "containers").glob("misconfiguration_report_container_*.json")
    ):
        trivy_data = _load_json_report(report_file)
        if trivy_data is None:
            continue
        name = report_file.stem.removeprefix("misconfiguration_report_container_")
        _merge(trivy_data, "container", name)

    output_path = reports_path / "consolidated_misconfiguration_report.json"
    with open(output_path, "w") as f:
        json.dump(consolidated, f, indent=2)
    logger.info(
        f"Consolidated misconfiguration report saved at {output_path} "
        f"({len(consolidated)} unique rule violations)"
    )
    return output_path


def consolidate_sbom_reports(reports_path: Path) -> Path:
    """Merge every per-container CycloneDX SBOM (sboms/sbom_*.json) under
    `reports_path` into one package-keyed JSON. Deduplicates by purl (falls back
    to name@version for components without one); each entry lists every container
    that includes it. Returns the path of the written file."""
    consolidated: dict[str, dict] = {}

    for report_file in sorted((reports_path / "sboms").glob("sbom_*.json")):
        bom = _load_json_report(report_file)
        if bom is None:
            continue
        artifact_name = report_file.stem.removeprefix("sbom_")
        for component in bom.get("components", []):
            key = component.get("purl") or f"{component.get('name')}@{component.get('version')}"
            if key not in consolidated:
                licenses = []
                for lic in component.get("licenses") or []:
                    license_info = lic.get("license") or {}
                    label = license_info.get("id") or license_info.get("name")
                    if label:
                        licenses.append(label)
                consolidated[key] = {
                    "Name": component.get("name", ""),
                    "Version": component.get("version", ""),
                    "Type": component.get("type", ""),
                    "Licenses": licenses,
                    "Artifacts": [],
                }
            artifact = {"name": artifact_name, "type": "container"}
            if artifact not in consolidated[key]["Artifacts"]:
                consolidated[key]["Artifacts"].append(artifact)

    output_path = reports_path / "consolidated_sbom_report.json"
    with open(output_path, "w") as f:
        json.dump(consolidated, f, indent=2)
    logger.info(
        f"Consolidated SBOM report saved at {output_path} ({len(consolidated)} unique packages)"
    )
    return output_path
