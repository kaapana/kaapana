#!/usr/bin/env python3
from glob import glob
import shutil
import yaml
import os
import json
from datetime import datetime
from treelib import Tree
from subprocess import PIPE, run
from os.path import join, dirname, basename, exists, isfile, isdir
from pathlib import Path
from build_helper.build_utils import BuildUtils
from build_helper.container_helper import Container, pull_container_image
from jinja2 import Environment, FileSystemLoader
from multiprocessing.pool import ThreadPool
import networkx as nx
from alive_progress import alive_bar
from build_helper.security_utils import TrivyUtils
from build_helper.offline_installer_helper import OfflineInstallerHelper

suite_tag = "Charts"
os.environ["HELM_EXPERIMENTAL_OCI"] = "1"
successful_built_containers = []

def parallel_execute(container_object):
    queue_id, container_object = container_object
    done = True
    issue = None

    for base_container in container_object.base_images:
        if base_container.local_image and base_container.tag not in successful_built_containers:
            done = False
            return queue_id, container_object, issue, done

    issue = container_object.build()
    if issue == None:
        successful_built_containers.append(container_object.build_tag)
        issue = container_object.push()

    return queue_id, container_object, issue, done


def generate_deployment_script(platform_chart):
    BuildUtils.logger.info(f"-> Generate platform deployment script for {platform_chart.name} ...")
    file_loader = FileSystemLoader(join(BuildUtils.kaapana_dir, "platforms"))  # directory of template file
    env = Environment(loader=file_loader)

    deployment_script_config_path = list(Path(platform_chart.chart_dir).rglob("deployment_config.yaml"))

    if len(deployment_script_config_path) != 1:
        BuildUtils.logger.error(f"Could not find platform deployment-script config for {platform_chart.name} at {dirname(platform_chart.chart_dir)}")
        BuildUtils.logger.error(f"{deployment_script_config_path=}")
        BuildUtils.generate_issue(
            component=suite_tag,
            name="generate_deployment_script",
            msg=f"Could not find platform deployment-script config for {platform_chart.name} at {dirname(platform_chart.chart_dir)}",
            level="ERROR"
        )
        return

    platform_params = yaml.load(open(deployment_script_config_path[0]), Loader=yaml.FullLoader)
    platform_params["platform_name"] = platform_chart.name
    platform_params["platform_build_version"] = BuildUtils.platform_build_version
    platform_params["container_registry_url"] = BuildUtils.default_registry
    if BuildUtils.include_credentials:
        platform_params["container_registry_username"] = BuildUtils.registry_user
        platform_params["container_registry_password"] = BuildUtils.registry_pwd

    platform_params["kaapana_collections"] = []

    if len(platform_chart.kaapana_collections) > 0:
        for collection_name, collection_chart in platform_chart.kaapana_collections.items():
            platform_params["kaapana_collections"].append({
                "name":  collection_chart.name,
                "version":   BuildUtils.platform_build_version
            })

    platform_params["preinstall_extensions"] = []
    if len(platform_chart.preinstall_extensions) > 0:
        for preinstall_extension_name, preinstall_extension_chart in platform_chart.preinstall_extensions.items():
            platform_params["preinstall_extensions"].append({
                "name":  preinstall_extension_chart.name,
                "version":   BuildUtils.platform_build_version
            })

    template = env.get_template('deploy_platform_template.sh')  # load template file

    output = template.render(**platform_params)

    platform_deployment_script_path_build = join(dirname(platform_chart.build_chart_dir), "deploy_platform.sh")
    if not os.path.exists(dirname(platform_deployment_script_path_build)):
        os.makedirs(dirname(platform_deployment_script_path_build))

    with open(platform_deployment_script_path_build, 'w') as rsh:
        rsh.write(output)

    os.chmod(platform_deployment_script_path_build, 0o775)
    BuildUtils.logger.debug(f"Deployment script generated.")


def generate_tree_node(chart_object, tree, parent):
    node_id = f"{parent}-{chart_object.name}"
    tree.create_node(chart_object.name, node_id, parent=parent)

    if len(chart_object.chart_containers) > 0:
        containers_node_id = f"{node_id}-containers"
        tree.create_node("containers", containers_node_id, parent=node_id)
        for container_tag, container in chart_object.chart_containers.items():
            container_node_id = f"{node_id}-{container.image_name}-{container.image_version}"
            tree.create_node(container.build_tag, container_node_id, parent=containers_node_id)

            if len(container.base_images) > 0:
                base_images_node_id = f"{container_node_id}-base-images"
                tree.create_node("base-images", base_images_node_id, parent=container_node_id)

            for base_image in container.base_images:
                base_img_node_id = f"{container_node_id}-{base_image.name}-{container.image_version}"
                tree.create_node(f"{base_image.name}:{base_image.version}", base_img_node_id, parent=base_images_node_id)

    if len(chart_object.dependencies) > 0:
        charts_node_id = f"{node_id}-charts"
        tree.create_node("sub-charts", charts_node_id, parent=node_id)
        for chart_id, dep_chart_object in chart_object.dependencies.items():
            tree = generate_tree_node(chart_object=dep_chart_object, tree=tree, parent=charts_node_id)

    return tree


def generate_nx_node(chart_object, graph, parent):
    node_id = f"chart:{chart_object.name}:{chart_object.repo_version}"
    graph.add_edge(parent, node_id)

    for container_tag, container in chart_object.chart_containers.items():
        container_node_id = f"container:{container.tag}"
        graph.add_edge(node_id, container_node_id)

        for base_image in container.base_images:
            base_img_node_id = f"base-image:{base_image.tag}"
            graph.add_edge(container_node_id, base_img_node_id)

    for chart_id, dep_chart_object in chart_object.dependencies.items():
        graph = generate_nx_node(chart_object=dep_chart_object, graph=graph, parent=node_id)

    return graph


def generate_build_graph(platform_chart):
    nx_build_graph = nx.DiGraph(directed=True)
    nx_build_graph.add_node("ROOT")

    tree = Tree()
    root_node_id = platform_chart.name
    tree.create_node(root_node_id, root_node_id.lower())

    nx_node_id = f"chart:{platform_chart.name}:{platform_chart.repo_version}"
    nx_build_graph.add_edge("ROOT", nx_node_id)
    for chart_id, chart_object in platform_chart.dependencies.items():
        tree = generate_tree_node(chart_object=chart_object, tree=tree, parent=root_node_id.lower())
        nx_build_graph = generate_nx_node(chart_object=chart_object, graph=nx_build_graph, parent=nx_node_id)

    if len(platform_chart.kaapana_collections) > 0:
        collections_root = f"{root_node_id.lower()}-collections"
        tree.create_node(collections_root, collections_root, parent=root_node_id.lower())
        for chart_id, chart_object in platform_chart.kaapana_collections.items():
            tree = generate_tree_node(chart_object=chart_object, tree=tree, parent=collections_root)
            nx_build_graph = generate_nx_node(chart_object=chart_object, graph=nx_build_graph, parent=nx_node_id)

    tree_json_path = join(BuildUtils.build_dir, platform_chart.name, f"tree-{platform_chart.name}.txt")
    tree.save2file(tree_json_path)
    BuildUtils.logger.info("")
    BuildUtils.logger.info("")
    BuildUtils.logger.info("BUILD TREE")
    BuildUtils.logger.info("")
    with open(tree_json_path, "r") as file:
        for line in file:
            BuildUtils.logger.info(line.strip('\n'))

    BuildUtils.logger.info("")

    return nx_build_graph


def helm_registry_login(username, password):
    BuildUtils.logger.info(f"-> Helm registry-logout: {BuildUtils.default_registry}")
    command = ["helm", "registry", "logout", BuildUtils.default_registry]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=10)

    if output.returncode != 0 and "Error: not logged in" not in output.stderr:
        BuildUtils.logger.info(f"Helm couldn't logout from registry: {BuildUtils.default_registry} -> not logged in!")

    BuildUtils.logger.info(f"-> Helm registry-login: {BuildUtils.default_registry}")
    command = ["helm", "registry", "login", BuildUtils.default_registry, "--username", username, "--password", password]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=10)

    if output.returncode != 0:
        BuildUtils.logger.error("Something went wrong!")
        BuildUtils.logger.error(f"Helm couldn't login into registry: {BuildUtils.default_registry}")
        BuildUtils.logger.error(f"Message: {output.stdout}")
        BuildUtils.logger.error(f"Error:   {output.stderr}")
        BuildUtils.generate_issue(
            component=suite_tag,
            name="helm_registry_login",
            msg=f"Helm couldn't login registry {BuildUtils.default_registry}",
            level="FATAL",
            output=output
        )


def check_helm_installed():
    command = ["which", "helm"]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=5)
    if output.returncode != 0:
        BuildUtils.logger.error("Helm is not installed!")
        BuildUtils.logger.error("-> install curl 'sudo apt install curl'")
        BuildUtils.logger.error("-> install helm 'sudo snap install helm --classic'!")
        BuildUtils.logger.error("-> install the kubeval 'helm plugin install https://github.com/instrumenta/helm-kubeval'")
        exit(1)

    command = ["helm", "kubeval", "--help"]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=5)
    if output.returncode != 0 or "The Kubernetes package manager" in output.stdout:
        BuildUtils.logger.error("Helm kubeval is not installed correctly!")
        BuildUtils.logger.error("Make sure Helm kubeval-plugin is installed!")
        BuildUtils.logger.error("hint: helm plugin install https://github.com/instrumenta/helm-kubeval")
        exit(1)


class HelmChart:
    registries_needed = None
    chart_containers = None
    kaapana_dir = None
    build_tree = None
    build_order_list = None
    save_tree = False
    enable_lint = True
    enable_kubeval = True
    enable_push = True
    max_tries = 5

    def __eq__(self, other):
        if isinstance(self, HelmChart) and isinstance(other, HelmChart):
            return self.chartfile == other.chartfile
        elif isinstance(self, str) and isinstance(other, HelmChart):
            return self == other.chart_id
        elif isinstance(self, HelmChart) and isinstance(other, str):
            return self.chart_id == other

    def get_dict(self):
        chart_dict = {
            "name": self.name,
            "repo_version": self.repo_version,
            "build_version": self.build_version,
            "chart_id": self.chart_id
        }
        return chart_dict

    def __init__(self, chartfile):
        self.name = None
        self.repo_version = None
        self.build_version = None
        self.build_branch = None
        self.last_commit_timestamp = None
        self.app_version = None
        self.chart_id = None
        self.kaapana_type = None
        self.ignore_linting = False
        self.chart_containers = {}
        self.log_list = []
        self.chartfile = chartfile
        self.dependencies = {}
        self.kaapana_collections = []
        self.preinstall_extensions = []
        self.dependencies_count_all = None
        self.values_yaml = None
        self.requirements_yaml = None
        self.chart_yaml = None
        self.build_chart_dir = None
        self.kubeval_done = False
        self.helmlint_done = False
        self.is_dag = False

        assert isfile(chartfile)

        self.path = self.chartfile
        with open(str(chartfile)) as f:
            self.chart_yaml = yaml.safe_load(f)

        self.chart_dir = dirname(chartfile)

        requirements_file = join(self.chart_dir, "requirements.yaml")
        if exists(requirements_file):
            with open(str(requirements_file)) as f:
                self.requirements_yaml = list(yaml.load_all(f, yaml.FullLoader))
            self.requirements_yaml = list(filter(None, self.requirements_yaml))
            if len(self.requirements_yaml) > 0:
                assert len(self.requirements_yaml) == 1
                self.requirements_yaml = self.requirements_yaml[0]
                try:
                    if self.requirements_yaml["dependencies"][0]["name"] == "dag-installer-chart":
                        self.is_dag = True
                except:
                    pass

            else:
                self.requirements_yaml = None

        values_file = join(self.chart_dir, "values.yaml")
        if exists(values_file):
            with open(str(values_file)) as f:
                self.values_yaml = list(yaml.load_all(f, yaml.FullLoader))
            self.values_yaml = list(filter(None, self.values_yaml))

            if len(self.values_yaml) > 0:
                assert len(self.values_yaml) == 1
                self.values_yaml = self.values_yaml[0]
            else:
                self.values_yaml = None

        assert "name" in self.chart_yaml
        self.name = self.chart_yaml["name"]

        if "appVersion" in self.chart_yaml:
            self.app_version = self.chart_yaml["appVersion"]

        if "version" in self.chart_yaml and self.chart_yaml["version"] != "0.0.0":
            self.repo_version = self.chart_yaml["version"]
        else:
            repo_version, build_branch, last_commit, last_commit_timestamp = BuildUtils.get_repo_info(self.chart_dir)
            self.repo_version = repo_version

        self.ignore_linting = False
        if "ignore_linting" in self.chart_yaml:
            self.ignore_linting = self.chart_yaml["ignore_linting"]

        self.chart_id = f"{self.name}"
        # self.chart_id = f"{self.name}:{self.app_version}"
        BuildUtils.logger.debug(f"{self.chart_id}: chart init")

        if "kaapana_type" in self.chart_yaml:
            self.kaapana_type = self.chart_yaml["kaapana_type"].lower()
        elif "keywords" in self.chart_yaml and "kaapanaworkflow" in self.chart_yaml["keywords"]:
            self.kaapana_type = "kaapanaworkflow"

        if self.kaapana_type == "platform":
            deployment_config = glob(self.chart_dir+"/deployment_config.yaml", recursive=True)
            assert len(deployment_config) == 1

            deployment_config = deployment_config[0]
            platform_params = yaml.load(open(deployment_config), Loader=yaml.FullLoader)
            if "kaapana_collections" in platform_params:
                self.kaapana_collections = platform_params["kaapana_collections"]

            if "preinstall_extensions" in platform_params:
                self.preinstall_extensions = platform_params["preinstall_extensions"]

        self.check_container_use()

    def add_dependency_by_id(self, dependency_name, dependency_version):
        if dependency_name in self.dependencies:
            BuildUtils.logger.info(f"{self.chart_id}: check_dependencies {dependency_name} already present.")

        charts_found = [x for x in BuildUtils.charts_available if x.name == dependency_name]
        # chart_available = [x for x in BuildUtils.charts_available if f"{x.name}-{x.repo_version}" == f"{dependency_name}-{dependency_version}"]

        if len(charts_found) > 1:
            BuildUtils.logger.warning(f"{self.chart_id}: Dependency-chart {dependency_name} -> multiple charts found -> checking version {dependency_version}")
            for chart_found in charts_found:
                BuildUtils.logger.warning(f"{self.chart_id}: Found version {chart_found.repo_version} at {chart_found.chart_dir}")
            charts_found = [x for x in charts_found if x.name == dependency_name and x.repo_version == dependency_version]
            BuildUtils.logger.warning(f"{self.chart_id}: Found {len(charts_found)} charts with version: {dependency_version}")
            
        if len(charts_found) == 1:
            dep_chart = charts_found[0]
            self.dependencies[dep_chart.chart_id] = dep_chart
            BuildUtils.logger.debug(f"{self.chart_id}: dependency found: {dep_chart.chart_id} at {dep_chart.chart_dir}")
        else:
            BuildUtils.logger.error(f"The correct dependency could not be identified! -> found:")
            for chart_found in charts_found:
                BuildUtils.logger.error(f"{chart_found.chart_id}: {chart_found.chartfile}")

            if len(charts_found) > 1:
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name=f"{self.chart_id}",
                    msg=f"check_dependencies failed! {dependency_name}: multiple charts found!",
                    level="ERROR"
                    )
            elif len(charts_found) == 0:
                BuildUtils.logger.error(f"{self.chart_id}: check_dependencies failed! {dependency_name} -> not found!")

                BuildUtils.generate_issue(
                    component=suite_tag,
                    name=f"{self.chart_id}",
                    msg=f"check_dependencies failed! Dependency {dependency_name} not found!",
                    level="ERROR"
                )

    def check_dependencies(self):
        if self.kaapana_type == "platform":
            self.check_collections()
            self.check_preinstall_extensions()

        BuildUtils.logger.debug(f"{self.chart_id}: check_dependencies")
        self.dependencies_count_all = 0
        requirements_file_path = join(self.chart_dir, "requirements.yaml")
        if exists(requirements_file_path):
            requirements_yaml = {}
            with open(str(requirements_file_path)) as f:
                requirements_yaml = yaml.safe_load(f)

            if requirements_yaml == None or "dependencies" not in requirements_yaml or requirements_yaml["dependencies"] == None:
                BuildUtils.logger.debug(f"{self.chart_id}: -> No dependencies defined")
                return

            self.dependencies_count_all = len(requirements_yaml["dependencies"])
            for dependency in requirements_yaml["dependencies"]:
                dependency_version = f"{dependency['version']}"
                if dependency_version == "0.0.0":
                    dependency_version = self.repo_version

                dependency_name = f"{dependency['name']}"
                self.add_dependency_by_id(dependency_name=dependency_name, dependency_version=dependency_version)

            BuildUtils.logger.debug(f"{self.chart_id}: found {len(self.dependencies)}/{self.dependencies_count_all} dependencies.")

            if len(self.dependencies) != self.dependencies_count_all:
                BuildUtils.logger.error(f"{self.chart_id}: check_dependencies failed! -> size self.dependencies vs dependencies_count_all")
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name=f"{self.chart_id}",
                    msg="chart check_dependencies failed! -> size self.dependencies vs dependencies_count_all",
                    level="ERROR",
                    path=self.chart_dir
                )

    def check_collections(self):
        BuildUtils.logger.debug(f"{self.chart_id}: check_collections")
        if not self.kaapana_collections or len(self.kaapana_collections) == 0:
            BuildUtils.logger.debug(f"{self.chart_id}: no kaapana_collections -> return")
            return

        config_kaapana_collections = self.kaapana_collections.copy()
        self.kaapana_collections = {}
        for collection in config_kaapana_collections:
            extension_collection_id = f"{collection['name']}"
            # extension_collection_id = f"{collection['name']}:{collection['version']}"
            collection_chart = [x for x in BuildUtils.charts_available if x == extension_collection_id]
            if len(collection_chart) == 1:
                self.kaapana_collections[collection_chart[0].chart_id] = collection_chart[0]
            else:
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name=f"{self.chart_id}",
                    msg=f"Platform extenstion-collection-chart: {extension_collection_id} could not be found!",
                    level="ERROR",
                    path=self.chart_dir
                )

    def check_preinstall_extensions(self):
        BuildUtils.logger.debug(f"{self.chart_id}: check_preinstall_extensions")
        if not self.preinstall_extensions or len(self.preinstall_extensions) == 0:
            BuildUtils.logger.debug(f"{self.chart_id}: no preinstall_extensions -> return")
            return

        config_preinstall_extensions = self.preinstall_extensions.copy()
        self.preinstall_extensions = {}
        for preinstall_extension in config_preinstall_extensions:
            preinstall_extension_id = f"{preinstall_extension['name']}"
            # extension_collection_id = f"{collection['name']}:{collection['version']}"
            preinstall_extension_chart = [x for x in BuildUtils.charts_available if x == preinstall_extension_id]
            if len(preinstall_extension_chart) == 1:
                self.preinstall_extensions[preinstall_extension_chart[0].chart_id] = preinstall_extension_chart[0]
            else:
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name=f"{self.chart_id}",
                    msg=f"Platform check_preinstall_extensions: {preinstall_extension_id} could not be found!",
                    level="ERROR",
                    path=self.chart_dir
                )

    def add_container_by_tag(self, container_registry,container_name,container_version):
        containers_found = [x for x in BuildUtils.container_images_available if x.image_name == container_name and x.registry == container_registry]

        if len(containers_found) == 1:
            container_found = containers_found[0]
            BuildUtils.logger.debug(f"{self.chart_id}: container found: {container_found.tag}")
            if container_found.tag not in self.chart_containers:
                self.chart_containers[container_found.tag] = container_found
            else:
                BuildUtils.logger.debug(f"{self.chart_id}: container already present: {container_found.tag}")

            if container_found.operator_containers != None:
                for operator_container in container_found.operator_containers:
                    oparator_container_found = [x for x in BuildUtils.container_images_available if x.tag == operator_container]
                    if len(oparator_container_found) == 1:
                        oparator_container_found = oparator_container_found[0]
                        if oparator_container_found.tag not in self.chart_containers:
                            self.chart_containers[oparator_container_found.tag] = oparator_container_found
                        else:
                            BuildUtils.logger.debug(f"{self.chart_id}: operator container already present: {oparator_container_found.tag}")
                    else:
                        BuildUtils.logger.error(f"Chart operator container needed {operator_container}")
                        BuildUtils.generate_issue(
                            component=suite_tag,
                            name=f"{self.chart_id}",
                            msg=f"Chart operator container not found in available images: {operator_container}",
                            level="ERROR",
                            path=self.chart_dir
                        )

        else:
            BuildUtils.logger.error(f"Chart container needed {container_name}")
            BuildUtils.logger.error(f"Chart container issue - found: {len(containers_found)}")
            if len(containers_found) > 1:
                for container_found in containers_found:
                    BuildUtils.logger.error(f"Dockerfile found: {container_found.path}")
            BuildUtils.generate_issue(
                component=suite_tag,
                name=f"{self.chart_id}",
                msg=f"Chart container not found in available images: {container_name}",
                level="ERROR",
                path=self.chart_dir
            )

    def check_container_use(self):
        BuildUtils.logger.debug(f"{self.chart_id}: check_container_use")

        if self.kaapana_type == "extenstion-collection":
            self.add_container_by_tag(container_registry=BuildUtils.default_registry,container_name=self.name,container_version=self.repo_version)

        elif self.values_yaml != None:  # if self.kaapana_type == "kaapanaworkflow":
            if "global" in self.values_yaml and self.values_yaml["global"] is not None and "image" in self.values_yaml["global"] and self.values_yaml["global"]["image"] != None:
                container_image = self.values_yaml["global"]["image"]

                container_version = None
                if "version" in self.values_yaml["global"]:
                    container_version = self.values_yaml["global"]["version"]
                else:
                    container_version = self.repo_version

                assert container_version != None
                assert container_image != None

                container_tag = f"{BuildUtils.default_registry}/{container_image}:{container_version}"
                self.add_container_by_tag(container_registry=BuildUtils.default_registry,container_name=container_image,container_version=container_version)

        template_dirs = (f"{self.chart_dir}/templates/*.yaml", f"{self.chart_dir}/crds/*.yaml")  # the tuple of file types
        files_grabbed = []
        for template_dir in template_dirs:
            files_grabbed.extend(glob(template_dir))
        for yaml_file in files_grabbed:

            # TODO -> currently not possible due to stringify the templating {{ test }} -> "{{ test }}"

            # with open(str(yaml_file)) as stream:
            #     try:
            #         yaml_contents = list(yaml.load_all(stream, yaml.UnsafeLoader))
            #     except Exception as e:
            #         BuildUtils.logger.error(f"{self.chart_id}: Issue with yaml-file: {yaml_file}")
            #         continue

            # container_kinds = ["Job","Deployment","Pod"]
            # for yaml_doc in yaml_contents:
            #     if yaml_doc != None and "kind" in yaml_doc:
            #         print(yaml_doc["kind"])
            #         if yaml_doc["kind"] in container_kinds:
            #             BuildUtils.logger.info("")
            #     if yaml_doc == None or "spec" not in yaml_doc:
            #         BuildUtils.logger.info("")
            #         continue
            #     elif "spec" not in yaml_doc["spec"]:
            #         BuildUtils.logger.info("")
            #         continue
            #     else:
            #         if  "image" not in yaml_doc["spec"]["spec"]:
            #             BuildUtils.logger.info("Not Found image")

            #         BuildUtils.logger.info("Found image")
            with open(yaml_file, "r") as yaml_content:
                for line in yaml_content:
                    line = line.rstrip()
                    if "image:" in line:
                        line = line.split("image:")[1].replace("\"", "").replace("'", "").replace("`", "").replace("$", "").replace(" ", "")
                        if "#" in line.split("image:")[0]:
                            BuildUtils.logger.debug(f"Commented: {line} -> skip")
                            continue
                        elif "-if" in line:
                            BuildUtils.logger.debug(f"Templated: {line} -> skip")
                            continue

                        elif ".Values.image" in line or ".Values.processing_image" in line or ".Values.global.image" in line or "collection.name" in line or "kube_helm_collection" in line:
                            BuildUtils.logger.debug(f"Templated image: {line} -> skip")
                            continue
                        else:
                            container_tag = line.replace("}", "").replace("{", "").replace(" ", "").replace("$", "")
                            container_tag = container_tag.replace(".Values.global.registry_url", BuildUtils.default_registry)
                            container_tag = container_tag.replace(".Values.global.kaapana_build_version", self.repo_version)
                            if "global" in container_tag.lower():
                                BuildUtils.logger.error(f"Templating could not be resolved for container-ID: {container_tag} ")
                                BuildUtils.generate_issue(
                                    component=suite_tag,
                                    name=f"{self.chart_id}",
                                    msg="Container extraction failed!",
                                    level="ERROR",
                                    path=self.chart_dir
                                )
                            
                            assert len(container_tag.split("/")) == 4 and len(container_tag.split(":")) == 2
                            container_version = container_tag.split(":")[-1]
                            container_name = container_tag.split(":")[0].split("/")[-1]
                            default_registry = "/".join(container_tag.split("/")[:3])
                            self.add_container_by_tag(container_registry=default_registry,container_name=container_name,container_version=container_version)

    def lint_chart(self, build_version=False):
        if self.helmlint_done:
            BuildUtils.logger.debug(f"{self.chart_id}: lint_chart already done - skip")
            return
        if HelmChart.enable_lint:
            BuildUtils.logger.info(f"{self.chart_id}: lint_chart")
            if build_version:
                cwd = self.build_chart_dir
            else:
                cwd = self.chart_dir

            command = ["helm", "lint"]
            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=20, cwd=cwd)
            if output.returncode != 0:
                BuildUtils.logger.error(f"{self.chart_id}: lint_chart failed!")
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name=f"{self.chart_id}",
                    msg="chart lint failed!",
                    level="WARNING",
                    output=output,
                    path=self.chart_dir
                )
            else:
                BuildUtils.logger.debug(f"{self.chart_id}: lint_chart ok")
                self.helmlint_done = True
        else:
            BuildUtils.logger.debug(f"{self.chart_id}: lint_chart disabled")

    def lint_kubeval(self, build_version=False):
        if self.kubeval_done:
            BuildUtils.logger.debug(f"{self.chart_id}: lint_kubeval already done -> skip")
            return

        if HelmChart.enable_kubeval:
            BuildUtils.logger.info(f"{self.chart_id}: lint_kubeval")
            if build_version:
                cwd = self.build_chart_dir
            else:
                cwd = self.chart_dir

            command = ["helm", "kubeval", "--ignore-missing-schemas", "."]
            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=20, cwd=cwd)
            if output.returncode != 0 and "A valid hostname" not in output.stderr:
                BuildUtils.logger.error(f"{self.chart_id}: lint_kubeval failed")
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name=f"{self.chart_id}",
                    msg="chart kubeval failed!",
                    level="WARNING",
                    output=output,
                    path=self.chart_dir
                )
            else:
                BuildUtils.logger.debug(f"{self.chart_id}: lint_kubeval ok")
                self.kubeval_done = True
        else:
            BuildUtils.logger.debug(f"{self.chart_id}: kubeval disabled")

    def make_package(self):
        BuildUtils.logger.info(f"{self.chart_id}: make_package")
        command = ["helm", "package", self.name]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60, cwd=dirname(self.build_chart_dir))
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
                path=self.chart_dir
            )

    def push(self):
        if HelmChart.enable_push:
            BuildUtils.logger.info(f"{self.chart_id}: push")
            try_count = 0
            command = ["helm", "push", f"{self.name}-{self.build_version}.tgz", f"oci://{BuildUtils.default_registry}"]
            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, cwd=dirname(self.build_chart_dir), timeout=60)
            while output.returncode != 0 and try_count < HelmChart.max_tries:
                BuildUtils.logger.warning(f"chart push failed -> try: {try_count}")
                output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, cwd=dirname(self.build_chart_dir), timeout=60)
                try_count += 1

            if output.returncode != 0 or "The Kubernetes package manager" in output.stdout:
                BuildUtils.logger.error(f"{self.chart_id}: push failed!")
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name=f"{self.chart_id}",
                    msg="chart push failed!",
                    level="ERROR",
                    output=output,
                    path=self.chart_dir
                )
            else:
                BuildUtils.logger.debug(f"{self.chart_id}: push ok")

        else:
            BuildUtils.logger.info(f"{self.chart_id}: push disabled")

    @staticmethod
    def collect_charts():
        charts_found = glob(BuildUtils.kaapana_dir+"/**/Chart.yaml", recursive=True)
        BuildUtils.logger.info("")
        BuildUtils.logger.info(f"Found {len(charts_found)} Charts in kaapana_dir")
        for external_source_dir in BuildUtils.external_source_dirs:
            BuildUtils.logger.info("")
            BuildUtils.logger.info(f"Searching for Charts in target_dir: {external_source_dir}")
            charts_found.extend(glob(external_source_dir+"/**/Chart.yaml", recursive=True))
            BuildUtils.logger.info(f"Found {len(charts_found)} Charts")

        if len(charts_found) != len(set(charts_found)):
            BuildUtils.logger.warning("-> Duplicate Charts found!")

        charts_found = sorted(set(charts_found), key=lambda p: (-p.count(os.path.sep), p))

        BuildUtils.logger.info("")
        BuildUtils.logger.info(f"--> Found {len(charts_found)} Charts across sources")
        BuildUtils.logger.info("")
        BuildUtils.logger.info("Generating Chart objects ...")
        BuildUtils.logger.info("")

        charts_objects = []
        with alive_bar(len(charts_found), dual_line=True,title='Collect-Charts') as bar:
            for chartfile in charts_found:
                bar()
                if BuildUtils.build_ignore_patterns != None and len(BuildUtils.build_ignore_patterns) > 0 and sum([ignore_pattern in chartfile for ignore_pattern in  BuildUtils.build_ignore_patterns]) != 0:
                    BuildUtils.logger.debug(f"Ignoring chart {chartfile}")
                    continue
                chart_obj = HelmChart(chartfile)
                bar.text(chart_obj.name)
                charts_objects.append(chart_obj)

        BuildUtils.add_charts_available(charts_available=charts_objects)

        return charts_objects

    @staticmethod
    def create_platform_build_files(platform_chart):
        BuildUtils.logger.info(f"{platform_chart.name}: create_platform_build_files")
        assert platform_chart.kaapana_type != None and platform_chart.kaapana_type == "platform"
        platform_build_files_base_target_dir = join(BuildUtils.build_dir, platform_chart.name)

        platform_build_files_target_dir = join(platform_build_files_base_target_dir, platform_chart.name)
        with alive_bar(bar='classic',spinner='crab',  dual_line=False,title='Generate Build-Version') as bar:
            HelmChart.create_chart_build_version(src_chart=platform_chart, target_build_dir=platform_build_files_target_dir,bar=bar)

        if len(platform_chart.kaapana_collections) > 0:
            for collection_name, collections_chart in platform_chart.kaapana_collections.items():
                BuildUtils.logger.info(f"{platform_chart.name} - {collection_name}: create create_collection_build_files")
                HelmChart.create_collection_build_files(collections_chart=collections_chart, platform_build_files_target_dir=platform_build_files_base_target_dir)

        platform_chart.lint_kubeval(build_version=True)

    @staticmethod
    def create_collection_build_files(collections_chart, platform_build_files_target_dir):
        # iterate over all collection_charts
        collection_build_target_dir = join(platform_build_files_target_dir, collections_chart.name)
        with alive_bar(bar='classic', spinner='crab',  dual_line=False,title='Generate Build-Version') as bar:
            HelmChart.create_chart_build_version(src_chart=collections_chart, target_build_dir=collection_build_target_dir,bar=bar)
        with alive_bar(collections_chart.dependencies_count_all,  dual_line=True, title='Generate Build-Version') as bar:
            for collection_chart_index, (collection_chart_name, collection_chart) in enumerate(collections_chart.dependencies.items()):
                BuildUtils.logger.info(f"Collection chart {collection_chart_index+1}/{collections_chart.dependencies_count_all}: {collection_chart_name}:")
                collection_chart_target_dir = join(collection_build_target_dir, "charts", collection_chart.name)
                collection_chart.make_package()
                bar()
        collection_container = [x for x in BuildUtils.container_images_available if collections_chart.name in x.tag]
        assert len(collection_container) == 1
        collection_container[0].container_dir = collection_build_target_dir

    @staticmethod
    def create_chart_build_version(src_chart, target_build_dir, bar=None):
        BuildUtils.logger.info(f"{src_chart.chart_id}: create_chart_build_version")

        src_chart.lint_chart(build_version=False)
        shutil.copytree(
            src=src_chart.chart_dir,
            dst=target_build_dir
        )

        # remove repositories from requirements.txt
        build_requirements = join(target_build_dir, "requirements.yaml")
        if os.path.exists(build_requirements):
            with open(build_requirements, "r") as f:
                build_requirements_lines = f.readlines()
            with open(build_requirements, "w") as f:
                for build_requirements_line in build_requirements_lines:
                    if "repository:" not in build_requirements_line.strip("\n"):
                        f.write(build_requirements_line)

        src_chart.build_chart_dir = target_build_dir
        src_chart.build_chartfile = join(target_build_dir, "Chart.yaml")

        assert exists(src_chart.build_chartfile)

        with open(src_chart.build_chartfile, "r") as f:
            chart_file_lines = f.readlines()
        with open(src_chart.build_chartfile, "w") as f:
            for chart_file_line in chart_file_lines:
                if "version:" in chart_file_line.strip("\n"):
                    f.write(f"version: \"{BuildUtils.platform_build_version}\"\n")
                else:
                    f.write(chart_file_line)

        # Update values.yaml of platform chartsdo to contain build meta information
        if src_chart.kaapana_type != None and src_chart.kaapana_type == "platform":
            src_chart.build_valuesfile = join(target_build_dir, "values.yaml")
            if not exists(src_chart.build_valuesfile):
                values = {}
            else:
                values = yaml.load(open(src_chart.build_valuesfile), Loader=yaml.FullLoader)

            if 'global' not in values:
                values['global'] = {}

            values['global'].update({
                'platform_build_branch': BuildUtils.platform_build_branch,
                'platform_last_commit_timestamp': BuildUtils.platform_last_commit_timestamp,
                'build_timestamp': datetime.now().strftime("%d-%m-%Y"),
                'kaapana_build_version': BuildUtils.platform_build_version
            })
            with open(src_chart.build_valuesfile, "w") as f:
                yaml.dump(values, f)


        for dep_chart_index, (dep_chart_key, dep_chart) in enumerate(src_chart.dependencies.items()):
            dep_chart_build_target_dir = join(target_build_dir, "charts", dep_chart.name)
            HelmChart.create_chart_build_version(src_chart=dep_chart, target_build_dir=dep_chart_build_target_dir,bar=bar)

            assert exists(dep_chart.build_chartfile)

        for chart_container_id, chart_container in src_chart.chart_containers.items():
            chart_container.build_tag = f"{BuildUtils.default_registry}/{chart_container.image_name}:{BuildUtils.platform_build_version}"
            chart_container.image_version = BuildUtils.platform_build_version
            chart_container.container_build_status = "None"
            chart_container.container_push_status = "None"
        
        if bar is not None:
            bar()
            bar.text=f"{src_chart.name}"

    @staticmethod
    def build_platform(platform_chart):
        BuildUtils.logger.info(f"-> Start platform-build for: {platform_chart.name}")

        repo_version, repo_branch, repo_last_commit, repo_last_commit_timestamp = BuildUtils.get_repo_info(platform_chart.chart_dir)

        BuildUtils.platform_name = platform_chart.name
        BuildUtils.platform_build_version = repo_version
        BuildUtils.platform_build_branch = repo_branch
        BuildUtils.platform_last_commit_timestamp = repo_last_commit_timestamp
        
        platform_chart.build_version = BuildUtils.platform_build_version
        
        HelmChart.create_platform_build_files(platform_chart=platform_chart)
        nx_graph = generate_build_graph(platform_chart=platform_chart)
        build_order = BuildUtils.get_build_order(build_graph=nx_graph)


        assert exists(platform_chart.build_chartfile)
        BuildUtils.logger.debug(f"creating chart package ...")
        platform_chart.make_package()
        platform_chart.push()
        BuildUtils.logger.info(f"{platform_chart.chart_id}: DONE")

        generate_deployment_script(platform_chart)

        BuildUtils.logger.info("")
        BuildUtils.logger.info("Start container build...")
        containers_to_built = []
        container_count = len(build_order)
        for i in range(0, container_count):
            container_id = build_order[i]
            container_to_build = [x for x in BuildUtils.container_images_available if x.tag == container_id]
            if len(container_to_build) == 1:
                container_to_build = container_to_build[0]
                if container_to_build.local_image and container_to_build.build_tag == None:
                    container_to_build.build_tag = container_to_build.tag

                containers_to_built.append(container_to_build)
            else:
                BuildUtils.logger.error(f"{container_id} could not be found in available containers!")
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name="container_build",
                    msg=f"{container_id} could not be found in available containers!",
                    level="FATAL"
                )
        containers_to_built_tmp = containers_to_built.copy()
        list_mid_index = len(containers_to_built) // 2
        for idx, container in enumerate(containers_to_built_tmp):
            org_list_idx = containers_to_built.index(container)
            local_base_image = False
            for base_image in container.base_images:
                if base_image.local_image:
                    local_base_image = True

            if container.local_image and not local_base_image:
                containers_to_built.insert(0, containers_to_built.pop(org_list_idx))

            elif container.local_image and local_base_image:
                containers_to_built.insert(list_mid_index, containers_to_built.pop(org_list_idx))

            elif not container.local_image and local_base_image:
                containers_to_built += [containers_to_built.pop(org_list_idx)]


        BuildUtils.logger.info("")
        BuildUtils.logger.info("")
        build_rounds = 0

        containers_to_built = [(x, containers_to_built[x]) for x in range(0, len(containers_to_built))]
        waiting_containers_to_built = containers_to_built.copy()
        with alive_bar(container_count, dual_line=True, title='Container-Build') as bar:
            while len(waiting_containers_to_built) != 0 and build_rounds <= BuildUtils.max_build_rounds:
                build_rounds += 1
                tmp_waiting_containers_to_built = []
                with ThreadPool(BuildUtils.parallel_processes) as threadpool:
                    result_containers = threadpool.imap_unordered(parallel_execute, containers_to_built)
                    for queue_id, result_container, issue, done in result_containers:
                        if not done:
                            BuildUtils.logger.info(f"{result_container.build_tag}: Base image not ready yet -> waiting list")
                            tmp_waiting_containers_to_built.append(result_container)
                        else:
                            bar()
                            if issue != None:

                                # Close threadpool if error is fatal
                                if BuildUtils.exit_on_error or issue["level"] == "FATAL":
                                    threadpool.terminate()
                                    threadpool.join()

                                bar.text(f"{result_container.tag}: ERROR")
                                BuildUtils.logger.info("")
                                BuildUtils.generate_issue(
                                    component=issue["component"],
                                    name=issue["name"],
                                    level=issue["level"],
                                    msg=issue["msg"],
                                    output=issue["output"] if "output" in issue else None,
                                    path=issue["path"] if "path" in issue else "",
                                )
                            else:
                                bar.text(f"{result_container.tag}: ok")

                waiting_containers_to_built = tmp_waiting_containers_to_built
        
        if build_rounds == BuildUtils.max_build_rounds:
            BuildUtils.generate_issue(
                component=suite_tag,
                name="container_build",
                msg=f"There were too many build-rounds! Still missing: {waiting_containers_to_built}",
                level="FATAL"
            )

        BuildUtils.logger.info("")
        BuildUtils.logger.info("")
        BuildUtils.logger.info("PLATFORM BUILD DONE.")

        # Scan for vulnerabilities if enabled
        if BuildUtils.vulnerability_scan is True:
            BuildUtils.logger.info("")
            BuildUtils.logger.info("")
            BuildUtils.logger.info("Starting vulnerability scan...")
            BuildUtils.logger.info("")
            BuildUtils.logger.info("")
            with alive_bar(len(successful_built_containers), dual_line=True, title='Vulnerability Scan') as bar:
                
                # Init trivy utils
                trivy_utils = TrivyUtils()

                # Loop through all built containers and scan them
                for image_build_tag in sorted(successful_built_containers):
                    # Set progress bar text
                    bar.text(image_build_tag)

                    # Create SBOM
                    trivy_utils.create_sbom(image_build_tag)

                    # Scan for vulnerabilities
                    trivy_utils.create_vulnerability_report(image_build_tag)

                    # Print progress bar
                    bar()

        if BuildUtils.create_offline_installation is True:
            OfflineInstallerHelper.generate_microk8s_offline_version()
            images_tarball_path = join(dirname(platform_chart.build_chart_dir),f"{platform_chart.name}-{platform_chart.build_version}-images.tar")
            OfflineInstallerHelper.export_image_list_into_tarball(image_list=successful_built_containers,images_tarball_path=images_tarball_path,timeout=4000)
            BuildUtils.logger.info("Finished: Generating platform images tarball.")

    @staticmethod
    def generate_platform_build_tree():
        charts_to_build = []
        for chart_object in BuildUtils.charts_available:
            if chart_object.kaapana_type != None and chart_object.kaapana_type == "platform":
                if BuildUtils.platform_filter != None and len(BuildUtils.platform_filter) != 0 and chart_object.name not in BuildUtils.platform_filter:
                    BuildUtils.logger.debug(f"Skipped {chart_object.chart_id} -> platform_filter set!")
                    continue

                BuildUtils.logger.info("")
                BuildUtils.logger.info("")
                BuildUtils.logger.info(f"Building platform-chart: {chart_object.chart_id}")
                BuildUtils.logger.info("")
                charts_to_build.append(chart_object)

                HelmChart.build_platform(platform_chart=chart_object)

        BuildUtils.generate_component_usage_info()


############################################################
######################   START   ###########################
############################################################


def init_helm_charts(enable_push=True, enable_lint=True, enable_kubeval=True, save_tree=False):
    BuildUtils.logger.info("Init build-system: Charts")
    HelmChart.save_tree = save_tree
    HelmChart.enable_lint = enable_lint
    HelmChart.enable_kubeval = enable_kubeval
    HelmChart.enable_push = enable_push

    check_helm_installed()


if __name__ == '__main__':
    print("Please use the 'start_build.py' script to launch the build-process.")
    exit(1)
