import re
from enum import Enum
from pathlib import Path
from subprocess import PIPE, run
from typing import Any, Dict, Optional, Set

import yaml
from build_helper_v2.core.container import Container
from build_helper_v2.models.build_config import BuildConfig
from build_helper_v2.services.container_service import ContainerService
from build_helper_v2.services.issue_tracker import IssueTracker
from build_helper_v2.utils.git_utils import GitUtils
from build_helper_v2.utils.logger import get_logger

logger = get_logger()

IMAGE_PATTERN = re.compile(
    r'image\s*=\s*f?["\']\{DEFAULT_REGISTRY\}/(?P<image_name>[^:]+):(?P<version>[^"\']+)["\']'
)


class KaapanaType(str, Enum):
    PLATFORM = "platform"  # kaapana-admin-chart, kaapana-platform-chart
    RUNTIME_ONLY = "runtime-only"  # pull-docker-images, update-collections

    KAAPANA_WORKFLOW = "kaapanaworkflow"  # total-segmentator, nnunet
    KAAPANA_APPLICATION = "kaapanaapplication"  # code-server-chart

    EXTENSION_COLLECTION = "extension-collection"
    SERVICE = "service"
    OTHER = "other"


class HelmChart:
    def __init__(
        self,
        name: str,
        chartfile: Path,
        is_dag: bool,
        kaapana_type: KaapanaType,
        version: str,
        ignore_linting: bool,
        chart_containers: Set[Container],
        unresolved_chart_dependencies: Set[tuple[str, str]],
        chart_dependencies: Optional[Set["HelmChart"]] = None,
        kaapana_collections: Optional[dict] = None,
        preinstall_extensions: Optional[dict] = None,
    ):
        self.name = name
        self.chartfile = chartfile
        self.is_dag = is_dag
        self.kaapana_type = kaapana_type
        self.version = version
        self.ignore_linting = ignore_linting
        self.chart_containers = chart_containers
        self.unresolved_chart_dependencies = unresolved_chart_dependencies
        self.linted = False
        self.chart_dependencies = chart_dependencies or set()
        self.kaapana_collections = kaapana_collections or {}
        self.preinstall_extensions = preinstall_extensions or {}

    def __repr__(self) -> str:
        return f"HelmChart({self.name=!r}, {self.version=!r}, {self.kaapana_type=})"

    def to_dict(self) -> Dict[str, str]:
        chart_dict = {
            "name": self.name,
            "version": self.version,
        }
        return chart_dict

    @classmethod
    def from_chartfile(cls, chartfile: Path, build_config: BuildConfig) -> "HelmChart":
        if not chartfile.exists():
            raise FileNotFoundError(f"Chart file not found: {chartfile}")

        chart_yaml = cls._load_yaml(chartfile)
        if not chart_yaml:
            raise FileNotFoundError(f"Cannot find a Chart.yaml document: {chartfile}")

        requirements = cls._load_yaml(chartfile.parent / "requirements.yaml")
        values = cls._load_yaml(chartfile.parent / "values.yaml")

        name = cls._resolve_chart_name(chart_yaml, chartfile)
        ignore_linting = chart_yaml.get("ingore_linging", False)
        version = cls._resolve_repo_version(chart_yaml, chartfile)
        is_dag = cls._has_dag_dependency(requirements)
        kaapana_type = cls._resolve_kaapana_type(chart_yaml, is_dag)

        logger.debug(f"{name}: chart init")

        chart_containers = cls._collect_chart_containers(
            chartfile=chartfile,
            values=values,
            kaapana_type=kaapana_type,
            name=name,
            version=version,
            build_config=build_config,
        )
        unresolved_chart_dependencies = cls._collect_chart_dependencies(
            chartfile=chartfile, repo_version=version
        )
        return cls(
            name=name,
            chartfile=chartfile,
            is_dag=is_dag,
            kaapana_type=KaapanaType(kaapana_type),
            version=version,
            ignore_linting=ignore_linting,
            chart_containers=chart_containers,
            unresolved_chart_dependencies=unresolved_chart_dependencies,
        )

    # ────────────────────────────────
    # Helper functions (static)
    # ────────────────────────────────

    @staticmethod
    def _load_yaml(path: Path) -> Optional[dict]:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            docs: list[dict] = list(
                filter(None, yaml.load_all(f, Loader=yaml.FullLoader))
            )
        if len(docs) > 1:
            raise ValueError(
                f"Expected a single YAML document in {path}, found {len(docs)}"
            )
        return docs[0] if docs else None

    @staticmethod
    def _resolve_chart_name(chart_yaml: dict, chartfile: Path) -> str:
        name = chart_yaml.get("name")
        if not name:
            raise ValueError(f"Missing 'name' in Chart.yaml: {chartfile}")
        return name

    @staticmethod
    def _resolve_repo_version(chart_yaml: dict, chartfile: Path) -> str:
        if chart_yaml.get("version") and chart_yaml["version"] != "0.0.0":
            return chart_yaml["version"]
        return GitUtils.get_repo_info(chartfile.parent)[0]

    @staticmethod
    def _has_dag_dependency(requirements: Optional[dict]) -> bool:
        deps = requirements.get("dependencies", []) if requirements else []
        return bool(deps) and deps[0].get("name") == "dag-installer-chart"

    @staticmethod
    def _resolve_kaapana_type(chart_yaml: dict, is_dag: bool) -> KaapanaType:
        yaml_type = chart_yaml.get("kaapana_type")
        if yaml_type:
            return KaapanaType(yaml_type.lower())

        # 2. Check DAG or keywords
        if is_dag or (
            "keywords" in chart_yaml and "kaapanaworkflow" in chart_yaml["keywords"]
        ):
            return KaapanaType("kaapanaworkflow")

        if "keywords" in chart_yaml and "kaapanaapplication" in chart_yaml["keywords"]:
            return KaapanaType("kaapanaapplication")

        return KaapanaType("other")

    @staticmethod
    def _collect_chart_dependencies(
        chartfile: Path,
        repo_version: str,
    ) -> Set[tuple[str, str]]:
        """
        Collect all dependencies for a Helm chart defined in requirements.yaml.
        Returns a list of HelmChart objects corresponding to the dependencies.
        """
        dependencies: Set[tuple[str, str]] = set()
        requirements_file = chartfile.parent / "requirements.yaml"

        if not requirements_file.exists():
            logger.debug(f"{chartfile}: No requirements.yaml -> no dependencies")
            return dependencies

        requirements_yaml = HelmChart._load_yaml(requirements_file)
        if not requirements_yaml or "dependencies" not in requirements_yaml:
            logger.debug(f"{chartfile}: requirements.yaml has no dependencies section")
            return dependencies
        for dep in requirements_yaml["dependencies"]:
            dep_name = dep.get("name")
            dep_version = dep.get("version", "0.0.0")
            if dep_version == "0.0.0":
                dep_version = GitUtils.get_repo_info(chartfile.parent)[0]
            else:
                dep_version = repo_version
            dependencies.add((dep_name, dep_version))
        return dependencies

    @classmethod
    def _collect_chart_containers(
        cls,
        chartfile: Path,
        values: Any,
        kaapana_type: str,
        name: str,
        version: str,
        build_config: BuildConfig,
    ) -> Set[Container]:
        chart_containers = set()

        # Collection container
        if kaapana_type == "runtime-only":
            return set()

        if kaapana_type == "extension-collection":
            collection_container = ContainerService.resolve_reference_to_container(
                registry=build_config.default_registry, image_name=name, version=version
            )
            chart_containers.add(collection_container)

        if kaapana_type == "kaapanaworkflow" and values:
            image = values.get("global", {}).get("image")
            workflow_container = ContainerService.resolve_reference_to_container(
                registry=build_config.default_registry,
                image_name=image,
                version=version,
            )
            chart_containers.add(workflow_container)
            operator_containers = cls.collect_operator_containers(
                chartfile=chartfile,
                default_registry=build_config.default_registry,
                version=version,
            )
            chart_containers |= operator_containers

        templates_containers = HelmChart.extract_images_from_templates(
            chartfile=chartfile,
            default_registry=build_config.default_registry,
            version=version,
            name=name,
        )
        chart_containers |= templates_containers

        return chart_containers

    @classmethod
    def collect_operator_containers(
        cls, chartfile: Path, version: str, default_registry: str
    ) -> Set[Container]:
        operator_containers: Set[Container] = set()
        python_files = (
            f
            for f in chartfile.parent.parent.glob("**/*.py")
            if "operator" in f.name.lower()
        )
        default_version = "{KAAPANA_BUILD_VERSION}"
        for python_file in python_files:
            with python_file.open("r", encoding="utf-8") as f:
                for line in f:
                    match = IMAGE_PATTERN.search(line)
                    if not match:
                        continue

                    image_name = match.group("image_name")
                    image_version = match.group(
                        "version"
                    )  # could be {KAAPANA_BUILD_VERSION} or fixed version

                    # Only process version if it's different from default
                    if image_version != default_version:
                        actual_version = image_version
                    else:
                        actual_version = version  # your default

                    operator_container = (
                        ContainerService.resolve_reference_to_container(
                            registry=default_registry,
                            image_name=image_name,
                            version=actual_version,
                        )
                    )
                    operator_containers.add(operator_container)
        return operator_containers

    @staticmethod
    def extract_images_from_templates(
        chartfile: Path,
        default_registry: str,
        version: str,
        name: str,
    ) -> Set[Container]:
        containers: Set[Container] = set()

        IMAGE_LINE_RE = re.compile(r"^\s*image:\s*(.+)$")

        template_dirs = [chartfile.parent / "templates", chartfile.parent / "crds"]
        yaml_files = [f for d in template_dirs if d.exists() for f in d.glob("*.yaml")]

        for yaml_file in yaml_files:
            try:
                for raw_line in yaml_file.read_text(encoding="utf-8").splitlines():
                    match = IMAGE_LINE_RE.match(raw_line)
                    if not match:
                        continue

                    # Remove unwanted literal characters
                    image_value = (
                        match.group(1)
                        .strip()
                        .translate(str.maketrans("", "", "\"'`$ "))
                    )

                    # Skip commented lines
                    if "#" in raw_line.split("image:")[0]:
                        logger.debug(f"Commented: {image_value} -> skip")
                        continue

                    # Skip known templating / test cases
                    if ("-if." in raw_line and "{{else}}" in raw_line) or (
                        "test_pull_image" in raw_line
                    ):
                        logger.debug(f"Templated: {image_value} -> skip")
                        continue

                    # Skip templated image references
                    if any(
                        t in image_value
                        for t in [
                            ".Values.image",
                            ".Values.global.complete_image",
                            ".Values.global.image",
                            "collection.name",
                            "kube_helm_collection",
                        ]
                    ):
                        logger.debug(f"Templated image: {image_value} -> skip")
                        continue

                    # Final cleanup
                    container_tag = (
                        image_value.replace("}", "")
                        .replace("{", "")
                        .replace(" ", "")
                        .replace("$", "")
                    )
                    container_tag = container_tag.replace(
                        ".Values.global.registry_url",
                        default_registry,
                    )
                    container_tag = container_tag.replace(
                        ".Values.global.kaapana_build_version",
                        version,
                    )
                    # Extract registry, name, version
                    container_registry = "/".join(container_tag.split("/")[:-1])
                    container_name = container_tag.split("/")[-1].split(":")[0]

                    container = ContainerService.resolve_reference_to_container(
                        registry=container_registry,
                        image_name=container_name,
                        version=version,
                    )
                    containers.add(container)

            except Exception as e:
                logger.error(f"Failed reading {yaml_file}: {e}")
                IssueTracker.generate_issue(
                    component=HelmChart.__name__,
                    name=name,
                    msg="Container extraction failed!",
                    level="ERROR",
                    path=chartfile.parent,
                )

        return containers

    def lint_chart(self, config: BuildConfig):
        if self.ignore_linting:
            logger.info(f"{self.name} has ignore_linting: true - skipping")
            return

        if self.linted:
            logger.debug(f"{self.name}: lint_chart already done - skip")
            return

        logger.info(f"{self.name}: lint_chart")

        cwd = self.build_chart_dir

        command = ["helm", "lint"]
        output = run(
            command,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=20,
            cwd=cwd,
        )
        if output.returncode != 0:
            logger.error(f"{self.name}: lint_chart failed!")
            IssueTracker.generate_issue(
                component=self.__class__.__name__,
                name=f"{self.name}",
                msg="chart lint failed!",
                level="WARNING",
                output=output,
                path=self.chartfile.parent,
            )
        else:
            logger.debug(f"{self.name}: lint_chart ok")
            self.helmlint_done = True

    def lint_kubeval(self, build_version=False):
        if self.ignore_linting:
            logger.info(f"{self.chart_id} has ignore_linting: true - skipping")
            return
        if self.kubeval_done:
            BuildUtils.logger.debug(
                f"{self.chart_id}: lint_kubeval already done -> skip"
            )
            return

        if HelmChart.enable_kubeval:
            BuildUtils.logger.info(f"{self.chart_id}: lint_kubeval")
            if build_version:
                cwd = self.build_chart_dir
            else:
                cwd = self.chart_dir

            command = ["helm", "kubeval", "--ignore-missing-schemas", "."]
            output = run(
                command,
                stdout=PIPE,
                stderr=PIPE,
                universal_newlines=True,
                timeout=20,
                cwd=cwd,
            )
            if output.returncode != 0 and "A valid hostname" not in output.stderr:
                BuildUtils.logger.error(f"{self.chart_id}: lint_kubeval failed")
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name=f"{self.chart_id}",
                    msg="chart kubeval failed!",
                    level="WARNING",
                    output=output,
                    path=self.chart_dir,
                )
            else:
                BuildUtils.logger.debug(f"{self.chart_id}: lint_kubeval ok")
                self.kubeval_done = True
        else:
            BuildUtils.logger.debug(f"{self.chart_id}: kubeval disabled")

    def make_package(self):
        BuildUtils.logger.info(f"{self.chart_id}: make_package")
        command = ["helm", "package", self.name]
        output = run(
            command,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=60,
            cwd=dirname(self.build_chart_dir),
        )
        if output.returncode == 0 and "Successfully" in output.stdout:
            BuildUtils.logger.debug(f"{self.chart_id}: package ok")
        else:
            BuildUtils.logger.error(f"{self.chart_id}: make_package failed!")
            BuildUtils.generate_issue(
                component=suite_tag,
                name=f"{self.chart_id}",
                msg="chart make_package failed!",
                level="ERROR",
                output=output,
                path=self.chart_dir,
            )

    def push(self):
        if HelmChart.enable_push:
            BuildUtils.logger.info(f"{self.chart_id}: push")
            try_count = 0
            command = [
                "helm",
                "push",
                f"{self.name}-{self.build_version}.tgz",
                f"oci://{BuildUtils.default_registry}",
            ]
            output = run(
                command,
                stdout=PIPE,
                stderr=PIPE,
                universal_newlines=True,
                cwd=dirname(self.build_chart_dir),
                timeout=60,
            )
            while output.returncode != 0 and try_count < HelmChart.max_tries:
                BuildUtils.logger.warning(f"chart push failed -> try: {try_count}")
                output = run(
                    command,
                    stdout=PIPE,
                    stderr=PIPE,
                    universal_newlines=True,
                    cwd=dirname(self.build_chart_dir),
                    timeout=60,
                )
                try_count += 1

            if (
                output.returncode != 0
                or "The Kubernetes package manager" in output.stdout
            ):
                BuildUtils.logger.error(f"{self.chart_id}: push failed!")
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name=f"{self.chart_id}",
                    msg="chart push failed!",
                    level="FATAL",
                    output=output,
                    path=self.chart_dir,
                )
            else:
                BuildUtils.logger.debug(f"{self.chart_id}: push ok")

        else:
            BuildUtils.logger.info(f"{self.chart_id}: push disabled")
