import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

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
    _threadpool: ThreadPoolExecutor = None  # type: ignore
    _kill_flag: bool = False
    _severity_levels: str = "CRITICAL,HIGH,MEDIUM,LOW,UNKNOWN"
    _trivy_image = "aquasec/trivy:0.65.0"
    _trivy_timeout = 10000

    @classmethod
    def init(cls, build_config: BuildConfig, build_state: BuildState):
        # vulnerability_scan: false # Whether containers should be checked for vulnerabilities during build.
        # vulnerability_severity_level: "CRITICAL,HIGH" # Filter by severity of findings. CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN. All -> ""
        # configuration_check: false # Wheter the Charts, deployments, dockerfiles etc. should be checked for configuration errors.
        # configuration_check_severity_level: "CRITICAL,HIGH" # Filter by severity of findings. CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN. All -> ""
        # create_sboms: false # Create Software Bill of Materials (SBOMs) for the built containers.
        # check_expired_vulnerabilities_database: false # Check if the vulnerability database is expired (6h) and rescan it if necessary.
        cls._build_config = build_config
        cls._build_state = build_state
        cls._reports_path = Path(build_config.build_dir) / "security-reports"
        cls._reports_path.mkdir(parents=True, exist_ok=True)
        cls._threadpool = ThreadPoolExecutor(
            max_workers=build_config.parallel_processes
        )

    @classmethod
    def _run_trivy(
        cls,
        target: str | Path,
        output_path: Path,
        mode: str = "image",  # "image" or "config"
        extra_args: list[str] | None = None,
    ):
        """
        Run Trivy for a given target.
        - mode=image   → scan container images
        - mode=config  → scan configs (Dockerfile, Helm charts, Kubernetes YAMLs)
        """
        output_path.mkdir(parents=True, exist_ok=True)

        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{output_path}:/trivy_results",
            cls._trivy_image,
        ]

        if isinstance(target, Path) and target.exists():
            # Mount parent folder
            cmd.extend(["-v", f"{target.parent}:/trivy_target"])
            target_path_inside = f"/trivy_target/{target.name}"
        else:  # image string
            target_path_inside = str(target)
            cmd.extend(["-v", "/var/run/docker.sock:/var/run/docker.sock"])

        # Add trivy mode
        if mode == "config":
            cmd.append("config")

        # Always JSON output for parsing
        if extra_args is None:
            extra_args = []
        if "--format" not in extra_args and "--output" not in extra_args:
            extra_args.extend(["--format", "json"])

        cmd.extend(extra_args)
        cmd.append(target_path_inside)

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=cls._trivy_timeout
        )
        if result.returncode != 0:
            logger.error(f"Trivy failed for {target}:\n{result.stderr}")
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )

        return result

    @classmethod
    def configuration_check(cls):
        for chart in cls._build_state.selected_charts:
            cls.check_chart(chart)

        for container in cls._build_state.selected_containers:
            cls.check_container(container)

    @classmethod
    def check_chart(cls, chart: HelmChart):
        chart_report_path = cls._reports_path / f"chart_report_{chart.name}.json"
        cls._run_trivy(
            chart.chartfile,
            cls._reports_path,
            mode="config",
            extra_args=["--output", str(chart_report_path)],
        )
        logger.info(f"Chart config report saved at {chart_report_path}")

    @classmethod
    def check_container(cls, container: Container):
        dockerfile_report_path = (
            cls._reports_path / f"dockerfile_{container.image_name}.json"
        )
        cls._run_trivy(
            container.dockerfile,
            cls._reports_path,
            mode="config",
            extra_args=["--output", str(dockerfile_report_path)],
        )
        logger.info(f"Dockerfile config report saved at {dockerfile_report_path}")

    @classmethod
    def create_sboms(cls):
        return NotImplemented

    @classmethod
    def vulnerability_scan(cls):
        return NotImplemented
