class TrivyUtils:
    trivy_image = "aquasec/trivy:0.57.1"
    timeout = 10000
    threadpool = None
    list_of_running_containers = []
    kill_flag = False
    cache = True
    tag = None
    dockerfile_report_path = None

    def __init__(self, cache=True, tag=None):
        if tag is None:
            raise Exception("Please provide a tag")

        self.tag
        self.cache = cache

        if BuildUtils.configuration_check:
            # Check if trivy is installed
            if which("trivy") is None:
                BuildUtils.logger.error(
                    "Trivy is not installed, please visit https://aquasecurity.github.io/trivy/v0.38/getting-started/installation/ for installation instructions. You must install Trivy version 0.38.1, higher is not supported yet."
                )
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name="Check if Trivy is installed",
                    msg="Trivy is not installed",
                    level="ERROR",
                )

        # Check if severity level is set (enable all vulnerabily severity levels if not set)
        if (
            BuildUtils.vulnerability_severity_level == ""
            or BuildUtils.vulnerability_severity_level == None
        ):
            BuildUtils.vulnerability_severity_level = "CRITICAL,HIGH,MEDIUM,LOW,UNKNOWN"
        # Check if vulnerability_severity_levels are in the allowed values
        elif not all(
            x in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]
            for x in BuildUtils.vulnerability_severity_level.split(",")
        ):
            BuildUtils.logger.warning(
                f"Invalid severity level set in vulnerability_severity_level: {BuildUtils.vulnerability_severity_level}. Allowed values are: CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN"
            )
            BuildUtils.generate_issue(
                component=suite_tag,
                name="Check if vulnerability_severity_level is set correctly",
                msg="Invalid severity level set in vulnerability_severity_level",
                level="ERROR",
            )

        run(["docker", "logout", "ghcr.io"], stdout=DEVNULL, stderr=DEVNULL)

        self.semaphore_sboms = threading.Lock()
        self.semaphore_vulnerability_reports = threading.Lock()
        self.semaphore_compressed_dockerfile_report = threading.Lock()
        self.semaphore_running_containers = threading.Lock()
        self.semaphore_threadpool = threading.Lock()

        self.threadpool = ThreadPool(BuildUtils.parallel_processes)

        # create reports path
        self.reports_path = os.path.normpath(
            os.path.join(BuildUtils.build_dir, "security-reports")
        )

        os.makedirs(self.reports_path, exist_ok=True)

        self.database_timestamp = self.get_database_next_update_timestamp()
