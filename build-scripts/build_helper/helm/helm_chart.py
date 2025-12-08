import re
import shutil
from datetime import datetime
from enum import Enum
from pathlib import Path
from subprocess import PIPE, run
from typing import Any, Dict, Optional, Set

import yaml
from build_helper.build import BuildConfig, IssueTracker
from build_helper.container import Container, ContainerHelper
from build_helper.utils import GitUtils, get_logger

logger = get_logger()

IMAGE_PATTERN = re.compile(
    r'^\s*-?\s*image\s*[:=]\s*f?["\']\{DEFAULT_REGISTRY\}/(?P<image_name>[^:]+):(?P<version>[^"\']+)["\']'
)


class KaapanaType(str, Enum):
    PLATFORM = "platform"  # kaapana-admin-chart, kaapana-platform-chart
    RUNTIME_ONLY = "runtime-only"  # pull-docker-images, update-collections

    KAAPANA_WORKFLOW = "kaapanaworkflow"  # old style workflows (v1)
    KAAPANA_WORKFLOW_V2 = (
        "kaapanaworkflow-v2"  # new style workflows with processingContainers
    )
    KAAPANA_APPLICATION = "kaapanaapplication"  # code-server-chart

    EXTENSION_COLLECTION = "extension-collection"

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
        chart_containers: set[Container],
        # String references to the chart before all of them are built
        unresolved_chart_dependencies: set[tuple[str, str]],
        deployment_config: dict[str, Any],
    ):
        self.name = name
        self.chartfile = chartfile
        self.is_dag = is_dag
        self.kaapana_type = kaapana_type
        self.version = version
        self.ignore_linting = ignore_linting
        self.chart_containers = chart_containers

        self.unresolved_chart_dependencies = unresolved_chart_dependencies

        self.deployment_config = deployment_config

        self.chart_dependencies: set["HelmChart"] = set()
        self.kaapana_collections: set["HelmChart"] = set()
        self.preinstall_extensions: list["HelmChart"] = []

        self.build_chart_dir: Path
        self.linted: bool = False
        self.kubeval_done: bool = False

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
        ignore_linting = chart_yaml.get("ignore_linting", False)
        if build_config.version_latest:
            version_str, *_ = GitUtils.get_repo_info(chartfile.parent)
            base = version_str.split("-")[0]
            version = f"{base}-latest"
        else:
            version = cls._resolve_repo_version(chart_yaml, chartfile)

        is_dag = cls._has_dag_dependency(requirements)
        kaapana_type = cls._resolve_kaapana_type(chart_yaml, is_dag)

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
        deployment_config: dict = {}
        if KaapanaType(kaapana_type) == KaapanaType.PLATFORM:
            deployment_config = cls._load_deployment_config(chartfile)

        return cls(
            name=name,
            chartfile=chartfile,
            is_dag=is_dag,
            kaapana_type=KaapanaType(kaapana_type),
            version=version,
            ignore_linting=ignore_linting,
            chart_containers=chart_containers,
            unresolved_chart_dependencies=unresolved_chart_dependencies,
            deployment_config=deployment_config,
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

        # Check keywords for workflow type
        keywords = chart_yaml.get("keywords", [])

        # Check DAG or v1 workflows
        if is_dag or "kaapanaworkflow" in keywords:
            return KaapanaType("kaapanaworkflow")

        # Check for v2 workflows
        if "kaapanaworkflow-v2" in keywords:
            return KaapanaType("kaapanaworkflow-v2")

        if "kaapanaapplication" in keywords:
            return KaapanaType("kaapanaapplication")

        return KaapanaType("other")

    @staticmethod
    def _collect_chart_dependencies(
        chartfile: Path,
        repo_version: str,
    ) -> Set[tuple[str, str]]:
        """
        Collect all dependencies for a Helm chart defined in Chart.yaml or requirements.yaml.
        Returns a set of tuples (name, version) for each dependency.
        """
        dependencies: Set[tuple[str, str]] = set()

        # First check Chart.yaml for Helm 3 style dependencies
        chart_yaml = HelmChart._load_yaml(chartfile)
        if chart_yaml and "dependencies" in chart_yaml:
            for dep in chart_yaml["dependencies"]:
                dep_name = dep.get("name")
                dep_version = dep.get("version", "0.0.0")
                if dep_version == "0.0.0":
                    dep_version = repo_version
                dependencies.add((dep_name, dep_version))

        # Also check requirements.yaml for Helm 2 compatibility
        requirements_file = chartfile.parent / "requirements.yaml"
        if requirements_file.exists():
            requirements_yaml = HelmChart._load_yaml(requirements_file)
            if requirements_yaml and "dependencies" in requirements_yaml:
                for dep in requirements_yaml["dependencies"]:
                    dep_name = dep.get("name")
                    dep_version = dep.get("version", "0.0.0")
                    if dep_version == "0.0.0":
                        dep_version = repo_version
                    dependencies.add((dep_name, dep_version))

        if not dependencies:
            logger.debug(
                f"{chartfile}: No dependencies found in Chart.yaml or requirements.yaml"
            )

        return dependencies

    @classmethod
    def _load_deployment_config(cls, chartfile: Path) -> dict[str, Any]:

        deployment_config_path = chartfile.parent / "deployment_config.yaml"

        if not deployment_config_path.exists():
            return {}

        try:
            with deployment_config_path.open("r", encoding="utf-8") as f:
                deployment_yaml = yaml.load(f, Loader=yaml.FullLoader) or {}

            deployment_config: dict[str, Any] = dict(deployment_yaml)

            # Normalize collections/extensions as sets
            deployment_config["kaapana_collections"] = {
                c.get("name")
                for c in deployment_yaml.get("kaapana_collections", [])
                if isinstance(c, dict) and "name" in c
            }

            deployment_config["preinstall_extensions"] = [
                e.get("name")
                for e in deployment_yaml.get("preinstall_extensions", [])
                if isinstance(e, dict) and "name" in e
            ]

            return deployment_config

        except Exception as exc:
            logger.warning(
                f"Failed to parse deployment_config.yaml for {chartfile}: {exc}"
            )
            return {}

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

        if kaapana_type == KaapanaType.EXTENSION_COLLECTION:
            collection_container = ContainerHelper.get_container(
                registry=build_config.default_registry, image_name=name, version=version
            )
            chart_containers.add(collection_container)

        if kaapana_type == KaapanaType.KAAPANA_WORKFLOW and values:
            # Check for workflow v1 style (global.image)
            image = values.get("global", {}).get("image")
            if image:
                workflow_container = ContainerHelper.get_container(
                    registry=build_config.default_registry,
                    image_name=image,
                    version=version,
                )
                chart_containers.add(workflow_container)

            # Scan for operator containers in Python files
            operator_containers = cls.collect_operator_containers(
                chartfile=chartfile,
                default_registry=build_config.default_registry,
                version=version,
            )
            chart_containers |= operator_containers

        # Workflow v2 - uses processingContainers list from values.yaml
        if kaapana_type == KaapanaType.KAAPANA_WORKFLOW_V2 and values:
            # Check for workflow v2 style (processingContainers list)
            processing_containers = values.get("processingContainers", [])
            for container_name in processing_containers:
                processing_container = ContainerHelper.get_container(
                    registry=build_config.default_registry,
                    image_name=container_name,
                    version=version,
                )
                chart_containers.add(processing_container)

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

                    operator_container = ContainerHelper.get_container(
                        registry=default_registry,
                        image_name=image_name,
                        version=actual_version,
                    )
                    operator_containers.add(operator_container)
        return operator_containers

    @staticmethod
    def process_line(line: str) -> str | None:
        """
        Try to extract an image reference from a line of YAML.
        Returns the cleaned image string or None if not applicable.
        """
        IMAGE_LINE_RE = re.compile(r"^\s*-?\s*image:\s*(.+)$")
        VALUES_IMAGE_RE = re.compile(r"^\s*-?\s*complete_image:\s*(.+)$")

        match = IMAGE_LINE_RE.match(line) or VALUES_IMAGE_RE.match(line)
        if not match:
            return None

        image_value = match.group(1).strip().translate(str.maketrans("", "", "\"'`$ "))

        # Skip commented lines
        if "#" in line.split(match.re.pattern.split(":")[0])[0]:
            logger.debug(f"Commented: {image_value} -> skip")
            return None

        # Skip known templating / test cases
        if ("-if." in line and "{{else}}" in line) or ("test_pull_image" in line):
            logger.debug(f"Templated: {image_value} -> skip")
            return None

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
            return None

        return image_value

    @classmethod
    def extract_images_from_templates(
        cls,
        chartfile: Path,
        default_registry: str,
        version: str,
        name: str,
    ) -> Set["Container"]:
        containers: Set["Container"] = set()

        template_dirs = [
            chartfile.parent / "templates",
            chartfile.parent / "crds",
            chartfile.parent,
        ]
        yaml_files = [f for d in template_dirs if d.exists() for f in d.glob("*.yaml")]

        for yaml_file in yaml_files:
            try:
                for raw_line in yaml_file.read_text(encoding="utf-8").splitlines():
                    image_value = cls.process_line(raw_line)

                    # If templated reference, check values.yaml
                    if image_value is None and any(
                        key in raw_line for key in ["image:", "complete_image:"]
                    ):
                        values_file = chartfile.parent / "values.yaml"
                        if values_file.exists():
                            for val_line in values_file.read_text(
                                encoding="utf-8"
                            ).splitlines():
                                image_value = cls.process_line(val_line)
                                if image_value:
                                    break

                    if not image_value:
                        continue

                    container_tag = cls._normalize_image_value(
                        image_value, default_registry, version
                    )
                    container_registry = (
                        "/".join(container_tag.split("/")[:-1]) or default_registry
                    )
                    container_name = container_tag.split("/")[-1].split(":")[0]

                    container = ContainerHelper.get_container(
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

    @staticmethod
    def _normalize_image_value(
        image_value: str, default_registry: str, version: str
    ) -> str:
        """Clean up templated image strings into a resolved image tag."""
        container_tag = (
            image_value.replace("}", "")
            .replace("{", "")
            .replace(" ", "")
            .replace("$", "")
        )
        container_tag = container_tag.replace(
            ".Values.global.registry_url", default_registry
        )
        container_tag = container_tag.replace(
            ".Values.global.kaapana_build_version", version
        )
        return container_tag

    @classmethod
    def extract_images_from_values(
        cls,
        chartfile: Path,
        default_registry: str,
        version: str,
        name: str,
    ) -> Set[Container]:
        """Scan values.yaml for 'complete_image:' entries."""
        containers: Set[Container] = set()
        values_file = chartfile.parent / "values.yaml"
        COMPLETE_IMAGE_RE = re.compile(r"^\s*complete_image:\s*(.+)$")
        if not values_file.exists():
            return containers

        try:
            for raw_line in values_file.read_text(encoding="utf-8").splitlines():
                match = COMPLETE_IMAGE_RE.match(raw_line)
                if not match:
                    continue

                image_value = (
                    match.group(1).strip().translate(str.maketrans("", "", "\"'`$ "))
                )

                container_tag = cls._normalize_image_value(
                    image_value, default_registry, version
                )

                container_registry = "/".join(container_tag.split("/")[:-1])
                container_name = container_tag.split("/")[-1].split(":")[0]

                container = ContainerHelper.get_container(
                    registry=container_registry,
                    image_name=container_name,
                    version=version,
                )
                containers.add(container)

        except Exception as e:
            logger.error(f"Failed reading {values_file}: {e}")
            IssueTracker.generate_issue(
                component=HelmChart.__name__,
                name=name,
                msg="Container extraction from values.yaml failed!",
                level="ERROR",
                path=chartfile.parent,
            )

        return containers

    def _update_values(self, target_dir: Path, version: str):
        """Update values.yaml with global build information for platform charts."""
        if self.kaapana_type != KaapanaType.PLATFORM:
            return

        values_file = target_dir / "values.yaml"
        values: dict = {}
        if values_file.exists():
            values = yaml.safe_load(values_file.read_text()) or {}

        # Ensure global section exists
        global_vals = values.setdefault("global", {})

        # Kaapana collections and preinstall extensions
        global_vals["kaapana_collections"] = [
            {"name": c.name, "version": version} for c in self.kaapana_collections
        ]
        global_vals["preinstall_extensions"] = [
            {"name": e.name, "version": version} for e in self.preinstall_extensions
        ]
        _, branch, commit, timestamp = GitUtils.get_repo_info(self.chartfile.parent)
        # Add build metadata
        global_vals.update(
            {
                "platform_build_branch": branch,
                "platform_last_commit_timestamp": timestamp,
                "build_timestamp": datetime.now()
                .astimezone()
                .replace(microsecond=0)
                .isoformat(),
                "kaapana_build_version": version,
            }
        )

        values_file.write_text(yaml.dump(values))

    def _update_requirements(self, target_dir: Path):
        build_requirements = target_dir / "requirements.yaml"
        if build_requirements.exists():
            with open(build_requirements, "r") as f:
                build_requirements_lines = f.readlines()
            with open(build_requirements, "w") as f:
                for build_requirements_line in build_requirements_lines:
                    if "repository:" not in build_requirements_line.strip("\n"):
                        f.write(build_requirements_line)

    def _update_chart_version(self, target_dir: Path, version: str):
        chart_file = target_dir / "Chart.yaml"
        with open(chart_file, "r") as f:
            lines = f.readlines()
        with open(chart_file, "w") as f:
            for line in lines:
                if line.startswith("version:"):
                    f.write(f'version: "{version}"\n')
                else:
                    f.write(line)

    def lint_chart(self, helm_executable: str, values: Optional[Path] = None):
        if self.ignore_linting:
            logger.debug(f"{self.name} has ignore_linting: true - skipping")
            return

        if self.linted:
            logger.debug(f"{self.name}: lint_chart already done - skip")
            return

        logger.info(f"{self.name}: lint_chart")

        command = [helm_executable, "lint", "."]
        if values:
            command = [helm_executable, "lint", ".", "--values", str(values)]
        output = run(
            command,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=20,
            cwd=self.build_chart_dir,
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
            self.linted = True

    def lint_kubeval(self, helm_executable: str, values: Optional[Path] = None):
        if self.ignore_linting:
            logger.debug(f"{self.name} has ignore_linting: true - skipping")
            return

        if self.kubeval_done:
            logger.debug(f"{self.name}: lint_kubeval already done -> skip")
            return

        logger.info(f"{self.name}: lint_kubeval")
        command = [helm_executable, "kubeval", "--ignore-missing-schemas", "."]
        if values:
            command.insert(-1, "--values")
            command.insert(-1, str(values))

        output = run(
            command,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=20,
            cwd=self.build_chart_dir,
        )
        if output.returncode != 0 and "A valid hostname" not in output.stderr:
            logger.error(f"{self.name}: lint_kubeval failed")
            IssueTracker.generate_issue(
                component=self.__class__.__name__,
                name=f"{self.name}",
                msg="chart kubeval failed!",
                level="WARNING",
                output=output,
                path=self.chartfile.parent,
            )
        else:
            logger.debug(f"{self.name}: lint_kubeval ok")
            self.kubeval_done = True

    def make_package(self, helm_executable: str, plain_http: bool):
        logger.info(f"{self.name}: make_package")
        command = [helm_executable, "package", self.name]
        if plain_http:
            command.append("--plain-http")

        output = run(
            command,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=60,
            cwd=self.build_chart_dir.parent,
        )
        if output.returncode == 0 and "Successfully" in output.stdout:
            logger.debug(f"{self.name}: package ok")
        else:
            logger.error(f"{self.name}: make_package failed!")
            IssueTracker.generate_issue(
                component=self.__class__.__name__,
                name=f"{self.name}",
                msg="chart make_package failed!",
                level="ERROR",
                output=output,
                path=self.chartfile.parent,
            )

    def push(
        self,
        helm_executable: str,
        default_registry: str,
        max_tries: int,
        plain_http: bool,
    ):
        logger.info(f"{self.name}: push")
        try_count = 0
        command = [
            helm_executable,
            "push",
            f"{self.name}-{self.version}.tgz",
            f"oci://{default_registry}",
        ]
        if plain_http:
            command.append("--plain-http")

        output = run(
            command,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            cwd=self.build_chart_dir.parent,
            timeout=60,
        )
        while output.returncode != 0 and try_count < max_tries:
            logger.warning(f"chart push failed -> try: {try_count}")
            output = run(
                command,
                stdout=PIPE,
                stderr=PIPE,
                universal_newlines=True,
                cwd=self.build_chart_dir,
                timeout=60,
            )
            try_count += 1

        if output.returncode != 0 or "The Kubernetes package manager" in output.stdout:
            logger.error(f"{self.name}: push failed!")
            IssueTracker.generate_issue(
                component=self.__class__.__name__,
                name=f"{self.name}",
                msg="chart push failed!",
                level="FATAL",
                output=output,
                path=self.chartfile.parent,
            )
        else:
            logger.debug(f"{self.name}: push ok")

    @staticmethod
    def _count_all_dependencies(
        chart: "HelmChart", seen: Optional[set[str]] = None
    ) -> int:
        """Count all recursive dependencies for a chart (no duplicates)."""
        if seen is None:
            seen = set()

        count = 0
        for dep in chart.chart_dependencies:
            if dep.name in seen:
                continue
            seen.add(dep.name)
            count += 1
            count += HelmChart._count_all_dependencies(dep, seen)

        return count

    def build(
        self,
        target_dir: Path,
        platform_build_version: str,
        bar=None,
        enable_linting=True,
        helm_executable: str = "helm",
        values=None,
    ) -> None:
        """
        Build only this chart into target_dir.
        No recursion — dependencies are handled by the caller.
        """
        self.build_chart_dir = target_dir
        logger.info(f"Building chart {self.name}:{self.version}")
        shutil.copytree(self.chartfile.parent, target_dir, dirs_exist_ok=True)

        # update Chart.yaml version
        self._update_chart_version(target_dir, version=platform_build_version)
        self._update_requirements(target_dir)

        # update values.yaml for platform
        if self.kaapana_type == KaapanaType.PLATFORM:
            self._update_values(target_dir, version=platform_build_version)

        for dep_chart in self.chart_dependencies:
            dep_chart.build(
                target_dir=target_dir / "charts" / dep_chart.name,
                platform_build_version=platform_build_version,
                bar=bar,
                enable_linting=enable_linting,
                values=values,
            )

        if enable_linting:
            self.lint_chart(helm_executable, values)
            self.lint_kubeval(helm_executable, values)

        if bar:
            bar()
            bar.text = f"{self.name}"
