import json
import queue
import shutil
import subprocess
import tempfile
import time
import uuid
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


def _load_json_report(report_file: Path) -> dict | None:
    """Load a Trivy/CycloneDX JSON report, or None if it's missing/malformed.
    A single bad file (e.g. from a killed job) shouldn't take the whole
    consolidated report down."""
    try:
        with open(report_file) as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.warning(f"Skipping unparseable scan report: {report_file}")
        return None


class SecurityScanner:
    """Trivy-based scanning for container misconfiguration/SBOM/vulnerability checks and vulnerability scanning of the raw snap packages from the offline installer."""

    _build_config: BuildConfig = None  # type: ignore
    _build_state: BuildState = None  # type: ignore
    _reports_path: Path = None  # type: ignore
    _cache_path: Path = None  # type: ignore
    _snap_reports_path: Path = None  # type: ignore
    _publish_path: Path = None  # type: ignore
    _worker_cache_pool: "queue.Queue | None" = None

    @classmethod
    def init(cls, build_config: BuildConfig, build_state: BuildState) -> None:
        """Initialize with configuration and build state, setting up report and cache directories."""
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
        cls._snap_reports_path = cls._reports_path / "snap_scans"
        cls._snap_reports_path.mkdir(parents=True, exist_ok=True)
        cls._publish_path = build_config.kaapana_dir / "reports"
        cls._publish_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _acquire_worker_cache(cls) -> Path:
        """Check out one worker's private copy of the shared trivy cache, creating a pool of `parallel_processes` copies on first use. The
        vulnerability + Java DB is close to a gigabyte on disk. Every target a worker processes reuses the same copy instead of paying for a fresh one."""
        if cls._worker_cache_pool is None:
            t0 = time.monotonic()
            pool: "queue.Queue" = queue.Queue()
            for _ in range(cls._build_config.parallel_processes):
                worker_cache = Path(
                    tempfile.mkdtemp(prefix=".trivy_worker_", dir=cls._reports_path)
                )
                shutil.copytree(cls._cache_path, worker_cache, dirs_exist_ok=True)
                pool.put(worker_cache)
            logger.info(
                f"[timing] prepared {cls._build_config.parallel_processes} trivy "
                f"cache copies in {time.monotonic() - t0:.1f}s"
            )
            cls._worker_cache_pool = pool
        return cls._worker_cache_pool.get()

    @classmethod
    def _release_worker_cache(cls, worker_cache: Path) -> None:
        cls._worker_cache_pool.put(worker_cache)

    @classmethod
    def cleanup(cls) -> None:
        """Remove the per-worker trivy-cache copies made by SBOM/vulnerability/
        snap scanning, if any were created. Safe to call even if none were —
        call once after all scanning for this run is done."""
        if cls._worker_cache_pool is None:
            return
        while not cls._worker_cache_pool.empty():
            shutil.rmtree(cls._worker_cache_pool.get(), ignore_errors=True)
        cls._worker_cache_pool = None

    # ------------------------------------------------------------------
    # Containers: misconfiguration, SBOM, vulnerability
    # ------------------------------------------------------------------

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
    def _ensure_checks_bundle(cls) -> None:
        """Download the Trivy checks (misconfiguration) bundle once before
        parallel config scans. `trivy config` has no download-only mode, so
        scanning an empty temp dir forces the bundle download as a side
        effect; it then lands in the shared cache and every worker skips its
        own update instead of racing to fetch it concurrently."""
        empty_dir = Path(
            tempfile.mkdtemp(prefix=".trivy_empty_", dir=cls._reports_path)
        )
        t0 = time.monotonic()
        try:
            cmd = [
                cls._build_config.trivy_executable,
                "config",
                "--cache-dir",
                str(cls._cache_path),
                "--format",
                "json",
                str(empty_dir),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode, cmd, output=result.stdout, stderr=result.stderr
                )
        finally:
            shutil.rmtree(empty_dir, ignore_errors=True)
        logger.info(f"[timing] checks bundle ensured in {time.monotonic() - t0:.1f}s")

    @classmethod
    def misconfiguration_check(cls) -> None:
        """Run Trivy misconfiguration scans on selected charts and containers."""
        cls._ensure_checks_bundle()
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
            "--skip-check-update",
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
            "--skip-check-update",
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
        """Download/update the Trivy vulnerability and Java DBs once before
        parallel scans (containers and snaps share this cache). Parallel
        workers all share the same cache dir, so concurrent DB updates
        deadlock on Trivy's file lock — and without a shared pre-fetch, every
        worker would instead pull the Java DB OCI artifact from the mirror at
        once, racing its redirect-based blob download into 404s."""
        t0 = time.monotonic()
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
        t1 = time.monotonic()

        cmd = [
            cls._build_config.trivy_executable,
            "image",
            "--cache-dir",
            str(cls._cache_path),
            "--download-java-db-only",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )
        logger.info(
            f"[timing] vuln DB ensured in {t1 - t0:.1f}s, "
            f"java DB ensured in {time.monotonic() - t1:.1f}s"
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
    def _create_sbom(cls, container: Container, report_path: Path) -> tuple[Path, bool, float]:
        """Generate SBOM for a single container. Returns (report_path, skipped, elapsed_seconds)."""
        filename = f"sbom_{container.image_name}.json"
        if (report_path / filename).exists():
            return report_path / filename, True, 0.0
        worker_cache = cls._acquire_worker_cache()
        try:
            # Trivy resolves the image via the local daemon first, then the
            # registry — daemon-less runners scan the pushed registry images.
            cmd = [
                cls._build_config.trivy_executable,
                "image",
                "--cache-dir",
                str(worker_cache),
                "--skip-db-update",
                "--skip-java-db-update",
                "--format",
                "cyclonedx",
                "--quiet",
                "--timeout",
                str(cls._build_config.trivy_timeout) + "s",
                "--output",
                str(report_path / filename),
                container.tag,
            ]
            t0 = time.monotonic()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=cls._build_config.trivy_timeout,
            )
            elapsed = time.monotonic() - t0
            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode, cmd, output=result.stdout, stderr=result.stderr
                )
            return report_path / filename, False, elapsed
        finally:
            cls._release_worker_cache(worker_cache)

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
                        path, skipped, elapsed = future.result()
                    except subprocess.CalledProcessError as e:
                        logger.error(f"SBOM generation failed for {container.tag}:\n{e.stderr}")
                        failures.append((container, e.stderr))
                    else:
                        if skipped:
                            logger.info(f"SBOM already exists, skipping: {path.name}")
                        else:
                            logger.info(f"[timing] SBOM saved at {path.name} in {elapsed:.1f}s")
                    bar()
        cls._fail_on_scan_errors("SBOM generation", failures)

    @classmethod
    def _scan_container_vuln(
        cls, container: Container, report_path: Path
    ) -> tuple[Path, bool, float]:
        """Run vulnerability scan for a single container. Returns (report_path, skipped, elapsed_seconds)."""
        filename = f"vuln_report_{container.image_name}.json"
        if (report_path / filename).exists():
            return report_path / filename, True, 0.0
        worker_cache = cls._acquire_worker_cache()
        ignore_file = files("build_cli") / "configs" / ".trivyignore.yaml"
        has_ignore = ignore_file.is_file()
        ignore_flag = ["--ignorefile", str(ignore_file)] if has_ignore else []
        try:
            # Trivy resolves the image via the local daemon first, then the
            # registry — daemon-less runners scan the pushed registry images.
            cmd = [
                cls._build_config.trivy_executable,
                "image",
                "--cache-dir",
                str(worker_cache),
                "--skip-db-update",
                "--skip-java-db-update",
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
            t0 = time.monotonic()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=cls._build_config.trivy_timeout,
            )
            elapsed = time.monotonic() - t0
            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode, cmd, output=result.stdout, stderr=result.stderr
                )
            return report_path / filename, False, elapsed
        finally:
            cls._release_worker_cache(worker_cache)

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
                        path, skipped, elapsed = future.result()
                    except subprocess.CalledProcessError as e:
                        logger.error(
                            f"Trivy vulnerability scan failed for {container.tag}:\n{e.stderr}"
                        )
                        failures.append((container, e.stderr))
                    else:
                        if skipped:
                            logger.info(f"Skipping (exists): {path.name}")
                        else:
                            logger.info(
                                f"[timing] Vulnerability report saved at {path.name} in {elapsed:.1f}s"
                            )
                    bar()
        cls._fail_on_scan_errors("Vulnerability scan", failures)

    # ------------------------------------------------------------------
    # Offline-installer snap packages
    # ------------------------------------------------------------------

    @classmethod
    def _scan_snap(cls, name: str, channel: str) -> tuple[Path, bool, dict]:
        """Download, extract, and Trivy-scan a single offline-installer snap
        package. Returns (report_path, skipped, timings). `trivy fs` can't
        analyze the Go binaries these snaps ship (microk8s, helm, snapd);
        `trivy rootfs` runs the same OS+language analyzers as `trivy image`
        against an extracted filesystem directly, no docker required."""
        report_path = cls._snap_reports_path / f"{name}.json"
        if report_path.exists():
            return report_path, True, {}

        timings: dict[str, float] = {}
        with tempfile.TemporaryDirectory(
            prefix=f".snap_scan_{name}_", dir=cls._reports_path
        ) as tmp:
            tmp_path = Path(tmp)
            rootfs = tmp_path / "rootfs"
            rootfs.mkdir()

            download_cmd = [
                "snap",
                "download",
                name,
                f"--channel={channel}",
                "--basename=pkg",
                f"--target-directory={tmp_path}",
            ]
            t0 = time.monotonic()
            result = subprocess.run(
                download_cmd,
                capture_output=True,
                text=True,
                timeout=cls._build_config.snap_download_timeout,
            )
            timings["download"] = time.monotonic() - t0
            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode,
                    download_cmd,
                    output=result.stdout,
                    stderr=result.stderr,
                )

            # -no-xattrs + tolerate errors: rootless unsquashfs cannot create
            # device nodes (e.g. in base snaps like core20) — irrelevant for
            # scanning; the file-count check below is the real success signal.
            t0 = time.monotonic()
            subprocess.run(
                [
                    "unsquashfs", "-q", "-n", "-f", "-no-xattrs",
                    "-d", str(rootfs), str(tmp_path / "pkg.snap"),
                ],
                capture_output=True,
                text=True,
            )
            timings["unsquashfs"] = time.monotonic() - t0
            if not any(rootfs.iterdir()):
                raise RuntimeError(f"snap extraction produced no files for {name}")
            # Some snaps ship mode-000 dirs (e.g. core20 var/lib/snapd/void);
            # trivy's gobinary analyzer also needs the execute bit preserved
            # to recognize a file as a binary worth analyzing.
            subprocess.run(["chmod", "-R", "u+rwX", str(rootfs)], check=True)

            worker_cache = cls._acquire_worker_cache()
            try:
                cmd = [
                    cls._build_config.trivy_executable,
                    "rootfs",
                    "--cache-dir",
                    str(worker_cache),
                    "--skip-db-update",
                    "--skip-java-db-update",
                    "--severity",
                    ",".join(cls._build_config.vulnerability_severity_level),
                    "--scanners",
                    "vuln",
                    "--format",
                    "json",
                    "--output",
                    str(report_path),
                    str(rootfs),
                ]
                t0 = time.monotonic()
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=cls._build_config.trivy_timeout,
                )
                timings["trivy"] = time.monotonic() - t0
                if result.returncode != 0:
                    raise subprocess.CalledProcessError(
                        result.returncode, cmd, output=result.stdout, stderr=result.stderr
                    )
            finally:
                cls._release_worker_cache(worker_cache)
        return report_path, False, timings

    @classmethod
    def offline_packages_scan(cls) -> None:
        """Scan every offline-installer snap package for vulnerabilities.
        Snap-store reachability is a newer, less-proven dependency than the
        container scan path, so failures here are logged and skipped — never
        raised — rather than failing the whole job."""
        cls._ensure_db()
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
                        path, skipped, timings = future.result()
                    except (subprocess.CalledProcessError, RuntimeError) as e:
                        logger.warning(
                            f"Snap vulnerability scan failed for {name} (non-fatal): {e}"
                        )
                    else:
                        if skipped:
                            logger.info(f"Skipping (exists): {path.name}")
                        else:
                            breakdown = ", ".join(
                                f"{step}={secs:.1f}s" for step, secs in timings.items()
                            )
                            logger.info(
                                f"[timing] Snap vulnerability report saved at "
                                f"{path.name} ({breakdown})"
                            )
                    bar()

    # ------------------------------------------------------------------
    # Report consolidation
    # ------------------------------------------------------------------

    @classmethod
    def _to_gitlab_report(cls, consolidated: dict) -> dict:
        """Convert the CVE-keyed consolidated report into GitLab's Container
        Scanning report format v2.0.0:
        https://gitlab.com/gitlab-org/security-products/security-report-schemas/-/blob/master/dist/container-scanning-report-format.json
        """
        gitlab_report = {
            "version": "2.0.0",
            "scan": {
                "scanner": {
                    "id": "trivy",
                    "name": "Trivy",
                    "url": "https://github.com/aquasecurity/trivy/",
                    "vendor": {"name": "GitLab"},
                    "version": "0.26.0",
                },
                "analyzer": {
                    "id": "gcs",
                    "name": "GitLab Container Scanning",
                    "vendor": {"name": "GitLab"},
                    "version": "5.1.0",
                },
                "type": "container_scanning",
                "start_time": "2022-05-19T12:47:33",
                "end_time": "2022-05-19T12:47:42",
                "status": "success",
            },
            "vulnerabilities": [],
        }

        for cve, vulnerability in consolidated.items():
            artifacts = vulnerability.get("Artifacts") or [
                {"name": "unknown", "type": "unknown"}
            ]
            gitlab_report["vulnerabilities"].append(
                {
                    "id": str(uuid.uuid4()),
                    "category": "container_scanning",
                    "message": vulnerability.get("Title") or cve,
                    "description": "TODO",
                    "severity": vulnerability.get("Severity", "Unknown").capitalize(),
                    "confidence": "High",
                    "scanner": {"id": "trivy", "name": "Trivy"},
                    "location": {
                        "dependency": {
                            "package": {"name": vulnerability.get("PkgName")},
                            "version": vulnerability.get("InstalledVersion"),
                        },
                        "operating_system": "TODO",
                        "image": ";".join(a["name"] for a in artifacts),
                    },
                    "identifiers": [{"type": "cve", "name": cve, "value": cve}],
                }
            )

        return gitlab_report

    @classmethod
    def _render_html_report(cls, consolidated: dict) -> str:
        """Render an interactive, filterable/sortable HTML vulnerability report
        from the CVE-keyed consolidated report."""
        rows = [
            {
                "cve": cve,
                "title": details.get("Title", ""),
                "pkg": details.get("PkgName", ""),
                "sev": details.get("Severity", "UNKNOWN").lower(),
                "installed": details.get("InstalledVersion", ""),
                "fixed": details.get("FixedVersion", "") or "—",
                "artifacts": details.get("Artifacts")
                or [{"name": "unknown", "type": "unknown"}],
            }
            for cve, details in consolidated.items()
        ]

        data_json = json.dumps(rows).replace("</script>", "<\\/script>")

        counts: dict[str, int] = {}
        for r in rows:
            counts[r["sev"]] = counts.get(r["sev"], 0) + 1
        parts = [
            f"{counts[s]} {s.capitalize()}"
            for s in ["critical", "high", "medium", "low"]
            if s in counts
        ]
        summary = f"{len(rows)} unique CVEs — " + ", ".join(parts)

        template = (
            files("build_cli") / "configs" / "interactive_report_template.html"
        ).read_text()
        return template.replace("__DATA_JSON__", data_json).replace(
            "__SUMMARY__", summary
        )

    @classmethod
    def consolidate_vulnerability_reports(cls) -> Path:
        """Merge every per-container (vuln_scan/vuln_report_*.json) and per-snap
        (snap_scans/*.json) Trivy report into one CVE-keyed JSON. Deduplicates by
        CVE ID; each CVE lists every artifact it was found in, tagged by type
        (container/snap) so a dashboard can tell them apart. Also publishes
        GitLab's container-scanning format and an interactive HTML report built
        from the same consolidated data. Returns the path of the consolidated
        JSON."""
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

        for report_file in sorted(
            (cls._reports_path / "vuln_scan").glob("vuln_report_*.json")
        ):
            trivy_data = _load_json_report(report_file)
            if trivy_data is None:
                continue
            artifact_name = trivy_data.get(
                "ArtifactName"
            ) or report_file.stem.removeprefix("vuln_report_")
            _merge(trivy_data, "container", artifact_name)

        for report_file in sorted(cls._snap_reports_path.glob("*.json")):
            trivy_data = _load_json_report(report_file)
            if trivy_data is None:
                continue
            _merge(trivy_data, "snap", report_file.stem)

        output_path = cls._publish_path / "consolidated_vulnerability_scan.json"
        with open(output_path, "w") as f:
            json.dump(consolidated, f, indent=2)
        logger.info(
            f"Consolidated vulnerability report saved at {output_path} ({len(consolidated)} unique CVEs)"
        )

        gitlab_report = cls._to_gitlab_report(consolidated)
        gitlab_report_path = cls._publish_path / "gl-container-scanning-report.json"
        with open(gitlab_report_path, "w") as f:
            json.dump(gitlab_report, f, indent=2)
        logger.info(f"GitLab container-scanning report saved at {gitlab_report_path}")

        html_report_path = cls._publish_path / "interactive_report.html"
        html_report_path.write_text(cls._render_html_report(consolidated))
        logger.info(f"Interactive HTML report saved at {html_report_path}")

        return output_path

    @classmethod
    def consolidate_misconfiguration_reports(cls) -> Path:
        """Merge every chart (charts/misconfiguration_report_chart_*.json) and container
        (containers/misconfiguration_report_container_*.json) Trivy config-scan report
        into one rule-ID-keyed JSON. Deduplicates by misconfiguration ID (e.g. DS-0002,
        KSV-0001); each entry lists every chart/container that failed it. Returns the
        path of the written file."""
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
            (cls._reports_path / "charts").glob("misconfiguration_report_chart_*.json")
        ):
            trivy_data = _load_json_report(report_file)
            if trivy_data is None:
                continue
            name = report_file.stem.removeprefix("misconfiguration_report_chart_")
            _merge(trivy_data, "chart", name)

        for report_file in sorted(
            (cls._reports_path / "containers").glob(
                "misconfiguration_report_container_*.json"
            )
        ):
            trivy_data = _load_json_report(report_file)
            if trivy_data is None:
                continue
            name = report_file.stem.removeprefix("misconfiguration_report_container_")
            _merge(trivy_data, "container", name)

        output_path = cls._publish_path / "consolidated_misconfiguration_check.json"
        with open(output_path, "w") as f:
            json.dump(consolidated, f, indent=2)
        logger.info(
            f"Consolidated misconfiguration report saved at {output_path} "
            f"({len(consolidated)} unique rule violations)"
        )
        return output_path

    @classmethod
    def consolidate_sbom_reports(cls) -> Path:
        """Merge every per-container CycloneDX SBOM (sboms/sbom_*.json) into one
        package-keyed JSON. Deduplicates by purl (falls back to name@version for
        components without one); each entry lists every container that includes
        it. Returns the path of the written file."""
        consolidated: dict[str, dict] = {}

        for report_file in sorted((cls._reports_path / "sboms").glob("sbom_*.json")):
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

        output_path = cls._publish_path / "consolidated_sbom.json"
        with open(output_path, "w") as f:
            json.dump(consolidated, f, indent=2)
        logger.info(
            f"Consolidated SBOM report saved at {output_path} ({len(consolidated)} unique packages)"
        )
        return output_path
