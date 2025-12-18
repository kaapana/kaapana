import argparse
import os
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for Kaapana Platform Builder.

    Uses `os.getenv()` so that arguments not set in the CLI
    are not included in the returned Namespace.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Kaapana Platform Builder")

    parser.add_argument(
        "-ll",
        "--log-level",
        help="Set logging verbosity (e.g. DEBUG, INFO, WARNING, ERROR).",
        default=os.getenv("LOG_LEVEL", "INFO"),
    )
    parser.add_argument(
        "-dr",
        "--default-registry",
        help="Name of the Docker registry to build and push images to.",
        default=os.getenv("DEFAULT_REGISTRY", ""),
    )
    parser.add_argument(
        "-pf",
        "--platform-filter",
        help="Comma-separated list of platform chart names to build.",
        default=os.getenv("PLATFORM_FILTER", "kaapana-admin-chart"),
    )
    parser.add_argument(
        "-es",
        "--external-source-dirs",
        help="Comma-separated external directories to search for containers and charts.",
        default=os.getenv("EXTERNAL_SOURCE_DIRS", ""),
    )
    parser.add_argument(
        "-bip",
        "--build-ignore-patterns",
        help="Comma-separated list of directories or files to exclude from build.",
        default=os.getenv(
            "BUILD_IGNORE_PATTERNS", "templates_and_examples,ci,lib/task_api"
        ),
    )
    parser.add_argument(
        "-u",
        "--registry-username",
        "--username",
        help="Username for registry authentication.",
        default=os.getenv(
            "REGISTRY_USER",
            "",
        ),
    )
    parser.add_argument(
        "-p",
        "--registry-password",
        "--password",
        help="Password for registry authentication.",
        default=os.getenv("REGISTRY_PW", ""),
    )
    parser.add_argument(
        "-bo",
        "--build-only",
        help="Only build containers and charts (do not push).",
        action="store_true",
        default=os.getenv("BUILD_ONLY", False),
    )
    parser.add_argument(
        "-el",
        "--enable-linting",
        help="Enable Helm chart linting and kubeval validation.",
        action="store_true",
        default=os.getenv("ENABLE_LINTING", True),
    )
    parser.add_argument(
        "-ee",
        "--exit-on-error",
        help="Stop the build process immediately if an error occurs.",
        action="store_true",
        default=os.getenv("EXIT_ON_ERROR", True),
    )
    parser.add_argument(
        "-pm",
        "--push-to-microk8s",
        help="Push built images into MicroK8s registry.",
        default=os.getenv("PUSH_TO_MICROK8S", False),
    )
    parser.add_argument(
        "-oi",
        "--create-offline-installation",
        help="Create a docker image dump for offline platform installation.",
        action="store_true",
        default=os.getenv("CREATE_OFFLINE_INSTALLATION", False),
    )
    parser.add_argument(
        "-pp",
        "--parallel-processes",
        help="Number of parallel processes for container build + push.",
        type=int,
        default=os.getenv("PARALLEL_PROCESSES", 2),
    )
    parser.add_argument(
        "-ic",
        "--include-credentials",
        help="Include registry credentials in deploy-platform script.",
        action="store_true",
        default=os.getenv("INCLUDE_CREDENTIALS", False),
    )
    parser.add_argument(
        "-vs",
        "--vulnerability-scan",
        help="Scan built containers with Trivy for vulnerabilities.",
        action="store_true",
        default=os.getenv("VULNERABILITY_SCAN", False),
    )
    parser.add_argument(
        "-vsl",
        "--vulnerability-severity-level",
        help="Filter vulnerabilities by severity (CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN).",
        default=os.getenv("VULNERABILTIY_SEVERITY_LEVEL", "CRITICAL,HIGH"),
    )
    parser.add_argument(
        "-cc",
        "--configuration-check",
        help="Check charts, deployments, Dockerfiles, etc. for configuration errors.",
        action="store_true",
        default=os.getenv("CONFIGURATION_CHECK", False),
    )
    parser.add_argument(
        "-ccl",
        "--configuration-check-severity-level",
        help="Filter configuration check findings by severity "
        "(CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN).",
        default=os.getenv("CONFIGURATION_CHECK_SEVERITY_LEVEL", "CRITICAL,HIGH"),
    )
    parser.add_argument(
        "-sbom",
        "--create-sboms",
        help="Generate SBOMs (Software Bill of Materials) for built containers.",
        action="store_true",
        default=os.getenv("CREATE_SBMOS", False),
    )
    parser.add_argument(
        "-is",
        "--enable-image-stats",
        help="Enable container image size statistics (writes image_stats.json).",
        action="store_true",
        default=os.getenv("ENABLE_IMAGE_STATS", False),
    )
    parser.add_argument(
        "--latest",
        dest="version_latest",
        help="Force version tag to 'latest'.",
        action="store_true",
        default=os.getenv("USE_LATEST_TAG", False),
    )
    parser.add_argument(
        "-cevd",
        "--check-expired-vulnerabilities-database",
        help="Check if vulnerability database is expired and rescan if necessary.",
        action="store_true",
        default=os.getenv("CEVD", False),
    )
    parser.add_argument(
        "-kd",
        "--kaapana-dir",
        help="Path to the Kaapana repository directory.",
        default=os.getenv(
            "KAAPANA_DIR", Path(__file__).resolve().parent.parent.parent.parent
        ),
    )
    parser.add_argument(
        "-bd",
        "--build-dir",
        help="Path to the directory for saving build artifacts.",
        default=os.getenv(
            "BUILD_DIR", Path(__file__).resolve().parent.parent.parent.parent / "build"
        ),
    )
    parser.add_argument(
        "-nl",
        "--no-login",
        help="Skip login to registry (expects to already be logged in).",
        action="store_true",
        default=os.getenv("NO_LOGIN", False),
    )
    parser.add_argument(
        "-i",
        "--interactive",
        help="Launch interactive selector to choose charts or containers to build.",
        action="store_true",
        default=os.getenv("INTERACTIVE", False),
    )
    parser.add_argument(
        "-cbc",
        "--containers-to-build-by-charts",
        help="Comma-separated list of Helm charts whose containers should be built "
        "(default: all containers used by platform charts).",
        default=os.getenv("CONTAINERS_TO_BUILD_BY_CHARTS", ""),
    )
    parser.add_argument(
        "-cb",
        "--containers-to-build",
        help="Comma-separated list of specific container images to build "
        "(default: all containers used by platform charts).",
        default=os.getenv("CONTAINERS_TO_BUILD", ""),
    )

    parser.add_argument(
        "-oc",
        "--only-charts",
        help="Skip docker build and docker push completely and only package and push charts",
        action="store_true",
        default=os.getenv("ONLY_CHARTS", False),
    )

    parser.add_argument(
        "--include-model-weights",
        help="Wether to download weights of pretrained models during the build of processing-containers like total-segmentator. This may take some time.",
        action="store_true",
        default=os.getenv("INCLUDE_MODEL_WEIGHTS", False),
    )

    parser.add_argument(
        "--http-proxy",
        help="HTTP proxy for outbound connections.",
        default=os.getenv("http_proxy", ""),
    )

    parser.add_argument(
        "--plain-http",
        help="Use plain HTTP for communication.",
        action="store_true",
        default=os.getenv("PLAIN_HTTP", False),
    )

    parser.add_argument(
        "--helm-executable",
        help="Helm executable to use.",
        default=os.getenv("HELM_EXECUTABLE", "helm"),
    )

    parser.add_argument(
        "--container-engine",
        help="Container engine to use (docker or podman).",
        default=os.getenv("CONTAINER_ENGINE", "docker"),
    )

    return parser.parse_args()
