#!/usr/bin/env python3
from glob import glob
import shutil
import yaml
import os
from treelib import Node, Tree
from subprocess import PIPE, run
from os.path import join, dirname, basename, exists, isfile, isdir
from time import time
from pathlib import Path
from build_helper.build_utils import BuildUtils

suite_tag = "Charts"
os.environ["HELM_EXPERIMENTAL_OCI"] = "1"


def generate_tree_node(chart_object, tree, parent):
    node_id = f"{parent}-{chart_object.name}"
    tree.create_node(chart_object.name, node_id, parent=parent)

    if len(chart_object.chart_containers) > 0:
        containers_node_id = f"{node_id}-containers"
        tree.create_node("containers", containers_node_id, parent=node_id)
        for container_tag, container in chart_object.chart_containers.items():
            container_node_id = f"{node_id}-{container.image_name}-{container.image_version}"
            tree.create_node(container.tag, container_node_id, parent=containers_node_id)

            if len(container.base_images) > 0:
                base_images_node_id = f"{container_node_id}-base-images"
                tree.create_node("base-images", base_images_node_id, parent=container_node_id)

            for base_image in container.base_images:
                base_img_node_id = f"{container_node_id}-{base_image.name}-{container.image_version}"
                tree.create_node(f"{base_image.name}-{base_image.version}", base_img_node_id, parent=base_images_node_id)

    if len(chart_object.dependencies) > 0:
        charts_node_id = f"{node_id}-charts"
        tree.create_node("sub-charts", charts_node_id, parent=node_id)
        for chart_id, dep_chart_object in chart_object.dependencies.items():
            tree = generate_tree_node(chart_object=dep_chart_object, tree=tree, parent=charts_node_id)

    return tree


def generate_nx_node(chart_object, parent):
    node_id = f"chart:{chart_object.name}:{chart_object.version}"
    BuildUtils.build_graph.add_edge(parent, node_id)

    for container_tag, container in chart_object.chart_containers.items():
        container_node_id = f"container:{container.tag}"
        BuildUtils.build_graph.add_edge(node_id, container_node_id)

        for base_image in container.base_images:
            base_img_node_id = f"base-image:{base_image.tag}"
            BuildUtils.build_graph.add_edge(container_node_id, base_img_node_id)

    for chart_id, dep_chart_object in chart_object.dependencies.items():
        generate_nx_node(chart_object=dep_chart_object, parent=node_id)


def generate_build_graph(charts_build_tree):
    for platform in charts_build_tree:

        tree = Tree()
        root_node_id = platform.name
        tree.create_node(root_node_id, root_node_id.lower())

        nx_node_id = f"chart:{platform.name}:{platform.version}"
        BuildUtils.build_graph.add_edge("ROOT", nx_node_id)
        for chart_id, chart_object in platform.dependencies.items():
            tree = generate_tree_node(chart_object=chart_object, tree=tree, parent=root_node_id.lower())
            generate_nx_node(chart_object=chart_object, parent=nx_node_id)

        if len(platform.collections) > 0:
            collections_root = f"{root_node_id.lower()}-collections"
            tree.create_node(collections_root, collections_root, parent=root_node_id.lower())
            for chart_id, chart_object in platform.collections.items():
                tree = generate_tree_node(chart_object=chart_object, tree=tree, parent=collections_root)
                generate_nx_node(chart_object=chart_object, parent=nx_node_id)

        tree_json_path = join(BuildUtils.build_dir, f"tree-{platform.name}.txt")
        tree.save2file(tree_json_path)
        BuildUtils.logger.info("")
        BuildUtils.logger.info("")
        BuildUtils.logger.info("BUILD TREE")
        BuildUtils.logger.info("")
        with open(tree_json_path, "r") as file:
            for line in file:
                BuildUtils.logger.info(line.strip('\n'))

        BuildUtils.logger.info("")


# def check_chart_containers(images_to_be_build, images_missing, chart_object):
#     for container, yaml in chart_object.chart_containers.items():
#         if "local-only" in container:
#             name = container.split("/")[-1].split(":")[0]
#             version = container.split("/")[-1].split(":")[1]
#         elif ".Values.global.registry_url" in container:
#             name = container.split("/")[-1].split(":")[0]
#             version = container.split("/")[-1].split(":")[1]
#         else:
#             BuildUtils.logger.error("Could not extract base-image!")
#             BuildUtils.generate_issue(
#                 component=suite_tag,
#                 name="check_chart_containers",
#                 msg="Could not extract base-image!",
#                 level="ERROR",
#             )
#         result_list = [x for x in BuildUtils.container_images_available if x.image_name == name and x.image_version == version]
#         if len(result_list) > 1:
#             BuildUtils.logger.error("Multiple containers found")
#             BuildUtils.generate_issue(
#                 component=suite_tag,
#                 name="check_chart_containers",
#                 msg="Multiple containers found",
#                 level="ERROR",
#             )
#         elif len(result_list) == 1:
#             chart_object.chart_containers[container] = f"{name}:{version} -> ok"
#             container_obj = result_list[0]
#             for base_image in container_obj.base_images:
#                 if base_image.local_image and base_image.tag not in BuildUtils.container_images_available:
#                     container.missing_base_images.append(base_image)
#                     BuildUtils.logger.error(f"-> {container.container_id} - base_image missing: {base_image.tag}")
#                     BuildUtils.generate_issue(
#                         component=suite_tag,
#                         name="check_chart_containers",
#                         msg=f"-> {container.container_id} - base_image missing: {base_image.tag}",
#                         level="ERROR",
#                     )
#                     if base_image.tag in BuildUtils.container_images_unused:
#                         BuildUtils.container_images_unused.remove(base_image.tag)

#             if container_obj in BuildUtils.container_images_unused:
#                 BuildUtils.container_images_unused.remove(container_obj)

#             if container_obj not in images_to_be_build:
#                 BuildUtils.logger.debug(f"Container: {name}:{version} found and added to build-list -> ok")
#                 images_to_be_build.append(container_obj)
#             else:
#                 BuildUtils.logger.debug(f"Container: {name}:{version} found but already presend in build-list -> ok")
#         else:
#             chart_object.chart_containers[container] = f"{name}:{version} -> missing !"
#             BuildUtils.logger.warn(f"Container: {name}:{version} not found in available containers! -> ERROR")
#             images_missing.append(f"{name}:{version}")

#     for dep_chart_id, dep_chart_object in chart_object.dependencies.items():
#         chart_object.images_to_be_build, chart_object.images_missing = check_chart_containers(images_to_be_build=images_to_be_build, images_missing=images_missing, chart_object=dep_chart_object)
#     return images_to_be_build, images_missing


# def check_container_availability(all_chart_objects):
#     images_to_be_build = []
#     images_missing = []
#     for chart_object in all_chart_objects:
#         chart_object.images_to_be_build, chart_object.images_missing = check_chart_containers(images_to_be_build=images_to_be_build, images_missing=images_missing, chart_object=chart_object)
#     return all_chart_objects


def helm_registry_login(username, password):
    BuildUtils.logger.info(f"-> Helm registry-logout: {BuildUtils.default_registry}")
    command = ["helm", "registry", "logout", BuildUtils.default_registry]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=10)

    if output.returncode != 0 and "Error: not logged in" not in output.stderr:
        BuildUtils.logger.error(f"Helm couldn't logout from registry: {BuildUtils.default_registry}")
        BuildUtils.generate_issue(
            component=suite_tag,
            name="helm_registry_login",
            msg=f"Helm couldn't logout from registry {BuildUtils.default_registry}",
            level="FATAL",
            output=output
        )
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
    command = ["helm", "kubeval", "--help"]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=5)
    if output.returncode != 0 or "The Kubernetes package manager" in output.stdout:
        BuildUtils.logger.error("Helm kubeval ist not installed correctly!")
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
            "version": self.version,
            "chart_id": self.chart_id
        }
        return chart_dict

    def __init__(self, chartfile):
        self.name = None
        self.version = None
        self.chart_id = None
        self.kaapana_type = None
        self.ignore_linting = False
        self.chart_containers = {}
        self.log_list = []
        self.chartfile = chartfile
        self.dependencies = {}
        self.collections = {}
        self.dependencies_count_all = None
        self.images_to_be_build = None

        assert isfile(chartfile)

        with open(str(chartfile)) as f:
            chart_yaml = yaml.safe_load(f)

        assert "name" in chart_yaml
        assert "version" in chart_yaml

        self.name = chart_yaml["name"]
        self.version = chart_yaml["version"]

        self.ignore_linting = False
        if "ignore_linting" in chart_yaml:
            self.ignore_linting = chart_yaml["ignore_linting"]

        self.kaapana_type = None
        if "kaapana_type" in chart_yaml:
            self.kaapana_type = chart_yaml["kaapana_type"].lower()

        self.path = self.chartfile
        self.chart_dir = dirname(chartfile)
        self.chart_id = f"{self.name}:{self.version}"
        BuildUtils.logger.debug(f"{self.chart_id}: chart init")
        self.check_container_use()

    def add_dependency_by_id(self, dependency_id):
        if dependency_id in self.dependencies:
            BuildUtils.logger.info(f"{self.chart_id}: check_dependencies {dependency_id} already present.")

        chart_available = [x for x in BuildUtils.charts_available if x == dependency_id]

        if len(chart_available) == 1:
            dep_chart = chart_available[0]
            self.dependencies[dep_chart.chart_id] = dep_chart
        else:
            BuildUtils.logger.warning(f"{self.chart_id}: check_dependencies failed! {dependency_id}")
            if len(chart_available) > 1:
                chart_identified = None
                BuildUtils.logger.warning(f"{self.chart_id}: Multiple dependency-charts found!")
                for external_project in BuildUtils.external_source_dirs:
                    for dep_chart in chart_available:
                        BuildUtils.logger.warning(f"{self.chart_id}: {dep_chart.chartfile}")
                        if external_project in self.chart_dir and external_project in dep_chart.chart_dir or \
                                BuildUtils.kaapana_dir in self.chart_dir and BuildUtils.kaapana_dir in dep_chart.chart_dir:
                            if chart_identified == None:
                                chart_identified = dep_chart
                            else:
                                chart_identified = False

                if chart_identified != False and chart_identified != None:
                    BuildUtils.logger.warning(f"{self.chart_id}: Identified dependency:")
                    BuildUtils.logger.warning(f"{self.chart_id}: {self.chart_dir} and")
                    BuildUtils.logger.warning(f"{self.chart_id}: {chart_identified.chart_dir}!")
                    BuildUtils.logger.warning(f"{self.chart_id}: -> using {chart_identified.chart_dir} as dependency..")
                    self.dependencies[chart_identified] = chart_identified.chart_id
                else:
                    BuildUtils.logger.warning(f"The right dependency could not be identified! -> found:")
                    for dep_found in chart_available:
                        BuildUtils.logger.warning(f"{dep_found.chart_id}: {dep_found.chartfile}")

                    BuildUtils.generate_issue(
                        component=suite_tag,
                        name=f"{self.chart_id}",
                        msg=f"check_dependencies failed! {dependency_id}: multiple charts found!",
                        level="ERROR"
                    )
            elif len(chart_available) == 0:
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name=f"{self.chart_id}",
                    msg=f"check_dependencies failed! Dependency {dependency_id} not found!",
                    level="ERROR"
                )

    def check_dependencies(self):
        if self.kaapana_type == "platform":
            self.check_collections()

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
                if "name" not in dependency or "version" not in dependency:
                    BuildUtils.generate_issue(
                        component=suite_tag,
                        name=f"{self.chart_id}",
                        msg="check_dependencies failed! -> name or version missing!",
                        level="ERROR"
                    )
                    return
                dependency_id = f"{dependency['name']}:{dependency['version']}"
                self.add_dependency_by_id(dependency_id=dependency_id)

                #     print("")
                # dep_chart_yaml = None

                # if dependency["repository"].startswith('file://deps'):
                #     dep_chart_yaml = join(self.chart_dir, dependency["repository"].replace("file://", ""), "Chart.yaml")

                # elif dependency["repository"].startswith('file://'):
                #     dep_dir = dirname(str(requirements_file))
                #     for i in range(0, dependency["repository"].count("../")):
                #         dep_dir = dirname(dep_dir)
                #     dep_chart_yaml = join(dep_dir, dependency["repository"].replace("file://", "").replace("../", ""), "Chart.yaml")

                # else:
                #     BuildUtils.logger.error(f"{self.chart_id}: check_dependencies failed! -> unknown dependency definition")
                #     BuildUtils.generate_issue(
                #         component=suite_tag,
                #         name=f"{self.chart_id}",
                #         msg="check_dependencies failed! -> unknown dependency definition",
                #         level="ERROR"
                #     )

                # if dep_chart_yaml == None or not isfile(dep_chart_yaml):
                #     BuildUtils.logger.error(f"{self.chart_id}: check_dependencies failed! -> issue with {dep_chart_yaml} ")
                #     BuildUtils.generate_issue(
                #         component=suite_tag,
                #         name=f"{self.chart_id}",
                #         msg=f"check_dependencies failed! -> issue with {dep_chart_yaml} ",
                #         level="ERROR"
                #     )

                # with open(dep_chart_yaml, 'r') as stream:
                #     chart_content = yaml.safe_load(stream)

                # if chart_content["version"] != dependency["version"]:
                #     BuildUtils.logger.error(f"{self.chart_id}: check_dependencies failed! -> version mismatch: dependency-version vs repo-version")
                #     BuildUtils.generate_issue(
                #         component=suite_tag,
                #         name=f"{self.chart_id}",
                #         msg=f"check_dependencies failed! -> version mismatch: dependency-version vs repo-version",
                #         level="ERROR"
                #     )

                # dep_chart_object = HelmChart(dep_chart_yaml)
                # dep_chart_object.check_dependencies()
                # dep_chart_object.lint_chart()
                # dep_chart_object.lint_kubeval()
                # dep_chart_object.check_container_use()
                # self.dependencies_list.append(dep_chart_object)

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
        values_path = join(self.chart_dir, "values.yaml")
        if not exists(values_path):
            BuildUtils.logger.debug(f"{self.chart_id}: no values.yaml found -> return")
            return

        with open(str(values_path)) as stream:
            yaml_content = list(yaml.load_all(stream, yaml.FullLoader))

        kaapana_collections = []
        for yaml_file in yaml_content:
            if yaml_file != None and "global" in yaml_file and "kube_helm_collections" in yaml_file["global"]:
                platform_collections = yaml_file["global"]["kube_helm_collections"]
                kaapana_collections.extend(platform_collections)

        for collection in kaapana_collections:
            extension_collection_id = f"{collection['name']}:{collection['version']}"
            collection_chart = [x for x in BuildUtils.charts_available if x == extension_collection_id]
            if len(collection_chart) == 1:
                extensions_container_tag = f"{BuildUtils.default_registry}/{collection['name']}:{collection['version']}"
                collection_chart = collection_chart[0]
                collection_chart.add_container_by_tag(extensions_container_tag)

                self.collections[collection_chart.chart_id] = collection_chart
            else:
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name=f"{self.chart_id}",
                    msg=f"Platform extenstion-collection-chart: {extension_collection_id} could not be found!",
                    level="ERROR",
                    path=self.chart_dir
                )

    def add_container_by_tag(self, container_tag):
        containers_found = [x for x in BuildUtils.container_images_available if x.tag == container_tag]
        if len(containers_found) == 1:
            container_found = containers_found[0]
            BuildUtils.logger.debug(f"{self.chart_id}: container found: {container_found.tag}")
            if container_found.tag not in self.chart_containers:
                self.chart_containers[container_found.tag] = container_found
            else:
                BuildUtils.logger.debug(f"{self.chart_id}: container already present: {container_found.tag}")

        else:
            BuildUtils.logger.error(f"Chart container needed {container_tag}")
            BuildUtils.logger.error(f"Chart container issue - found: {len(containers_found)}")
            BuildUtils.generate_issue(
                component=suite_tag,
                name=f"{self.chart_id}",
                msg=f"Chart container not found in available images: {container_tag}",
                level="ERROR",
                path=self.chart_dir
            )

    def check_container_use(self):
        BuildUtils.logger.debug(f"{self.chart_id}: check_container_use")

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
                            BuildUtils.logger.warn(f"Commented: {line} -> skip")
                            continue
                        elif "-if" in line:
                            BuildUtils.logger.warn(f"Templated: {line} -> skip")
                            continue

                        elif ".Values.image" in line or "collection.name" in line or "kube_helm_collection" in line:
                            BuildUtils.logger.warn(f"Templated image: {line} -> skip")
                            continue
                        else:
                            # container_tag = line.replace("{{.Values.global.registry_url}}", BuildUtils.default_registry)
                            # container_tag = line.replace("{{.Values.global.registry_url}}", BuildUtils.default_registry)
                            # container_tag = line.replace("{{.Values.global.registry_url}}", BuildUtils.default_registry)
                            container_tag = line.replace("}", "").replace("{", "").replace(" ", "").replace("$", "")
                            container_tag = container_tag.replace(".Values.global.registry_url", BuildUtils.default_registry)
                            container_tag = container_tag.replace(".Values.global.platform_abbr|defaultuk_", "")
                            container_tag = container_tag.replace(".Values.global.platform_version|default0__", "")
                            if "values" in container_tag.lower():
                                print()
                            self.add_container_by_tag(container_tag=container_tag)

    def dep_up(self, chart_dir=None, log_list=[]):
        BuildUtils.logger.debug(f"{self.chart_id}: dep_up")
        if chart_dir is None:
            chart_dir = self.chart_dir
            log_list = []

        dep_charts = join(chart_dir, "charts")
        if isdir(dep_charts):
            for item in os.listdir(dep_charts):
                path = join(dep_charts, item)
                if isdir(path):
                    log_list = self.dep_up(chart_dir=path, log_list=log_list)

        try_count = 0
        max_tries = 5

        os.chdir(chart_dir)
        command = ["helm", "dep", "up"]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60)
        while output.returncode != 0 and try_count < max_tries:
            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60)
            try_count += 1
        if output.returncode != 0:
            BuildUtils.logger.error(f"{self.chart_id}: dep_up failed!")
            BuildUtils.generate_issue(
                component=suite_tag,
                name=f"{self.chart_id}",
                msg="chart dep_up failed!",
                level="ERROR",
                output=output,
                path=self.chart_dir
            )

    def build_containers(self):
        BuildUtils.logger.debug(f"{self.chart_id}: build_containers")
        if self.images_to_be_build == None:
            BuildUtils.logger.debug(f"{self.chart_id}: No containers to build!")
            return
        for container_to_build in self.images_to_be_build:
            BuildUtils.logger.info("")
            BuildUtils.logger.info("")
            BuildUtils.logger.info("#########################################################################")
            BuildUtils.logger.info("")
            BuildUtils.logger.info(f"{self.chart_id}: building container: {container_to_build.container_id}")
            if container_to_build.already_built:
                BuildUtils.logger.info(f"{self.chart_id}: {container_to_build.container_id} was already build.")
            else:
                container_to_build.check_prebuild()
                container_to_build.build()
                container_to_build.push()

    def remove_tgz_files(self):
        BuildUtils.logger.debug(f"{self.chart_id}: remove_tgz_files")
        glob_path = '{}/charts'.format(self.chart_dir)
        for path in Path(glob_path).rglob('*.tgz'):
            os.remove(path)

        requirements_lock = '{}/requirements.lock'.format(self.chart_dir)
        if exists(requirements_lock):
            os.remove(requirements_lock)

    def lint_chart(self):
        if HelmChart.enable_lint:
            BuildUtils.logger.debug(f"{self.chart_id}: lint_chart")
            os.chdir(self.chart_dir)
            command = ["helm", "lint"]
            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=20)
            if output.returncode != 0:
                BuildUtils.logger.error(f"{self.chart_id}: lint_chart failed!")
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name=f"{self.chart_id}",
                    msg="chart lint failed!",
                    level="WARN",
                    output=output,
                    path=self.chart_dir
                )
            else:
                BuildUtils.logger.debug(f"{self.chart_id}: lint_chart ok")
        else:
            BuildUtils.logger.debug(f"{self.chart_id}: lint_chart disabled")

    def lint_kubeval(self):
        if HelmChart.enable_kubeval:
            BuildUtils.logger.info(f"{self.chart_id}: lint_kubeval")
            os.chdir(self.chart_dir)
            command = ["helm", "kubeval", "--ignore-missing-schemas", "."]
            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=20)
            if output.returncode != 0 and "A valid hostname" not in output.stderr:
                BuildUtils.logger.error(f"{self.chart_id}: lint_kubeval failed")
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name=f"{self.chart_id}",
                    msg="chart kubeval failed!",
                    level="WARN",
                    output=output,
                    path=self.chart_dir
                )
            else:
                BuildUtils.logger.debug(f"{self.chart_id}: lint_kubeval ok")
        else:
            BuildUtils.logger.debug(f"{self.chart_id}: kubeval disabled")

    def make_package(self):
        BuildUtils.logger.info(f"{self.chart_id}: make_package")
        os.chdir(dirname(self.chart_dir))
        command = ["helm", "package", self.name]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60)
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
            os.chdir(dirname(self.chart_dir))
            try_count = 0
            command = ["helm", "push", f"{self.name}-{self.version}.tgz", f"oci://{BuildUtils.default_registry}"]
            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60)
            while output.returncode != 0 and try_count < HelmChart.max_tries:
                BuildUtils.logger.info("Error push -> try: {}".format(try_count))
                output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60)
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

        charts_found = sorted(charts_found, key=lambda p: (-p.count(os.path.sep), p))

        BuildUtils.logger.info("")
        BuildUtils.logger.info(f"--> Found {len(charts_found)} Charts across sources")
        BuildUtils.logger.info("")
        BuildUtils.logger.info("Generating Chart objects ...")
        BuildUtils.logger.info("")

        charts_objects = []
        for chartfile in charts_found:
            if "templates_and_examples" in chartfile:
                BuildUtils.logger.debug(f"Skipping tutorial chart: {chartfile}")
                continue
            chart_obj = HelmChart(chartfile)

            chart_obj.remove_tgz_files()
            charts_objects.append(chart_obj)

        BuildUtils.add_charts_available(charts_available=charts_objects)

        return charts_objects

    @staticmethod
    def create_build_version(chart, parent_chart_dir=None):
        BuildUtils.logger.info(f"{chart.chart_id}: create_build_version")
        if parent_chart_dir == None:
            target_dir = join(BuildUtils.build_dir, chart.name)
        else:
            target_dir = join(parent_chart_dir, "charts", chart.name)

        shutil.copytree(
            src=chart.chart_dir,
            dst=target_dir
        )
        chart.build_chart_dir = target_dir
        chart.build_chartfile = join(target_dir, "Chart.yaml")
        requirements_path = join(target_dir, "requirements.yaml")
        if exists(requirements_path):
            with open(str(requirements_path)) as f:
                requirements_yaml = yaml.safe_load(f)
            if requirements_yaml != None and "dependencies" in requirements_yaml and requirements_yaml["dependencies"] != None:
                for dependency in requirements_yaml["dependencies"]:
                    if "repository" in dependency:
                        del dependency["repository"]

            with open(requirements_path, 'w') as outfile:
                yaml.dump(requirements_yaml, outfile, default_flow_style=False)

        deps_path = join(target_dir, "deps")
        if os.path.exists(deps_path):
            shutil.rmtree(deps_path)

        for dep_chart_id, dep_chart in chart.dependencies.items():
            HelmChart.create_build_version(chart=dep_chart, parent_chart_dir=target_dir)
            assert exists(dep_chart.build_chartfile)
            tmp_build_chart = HelmChart(chartfile=dep_chart.build_chartfile)
            tmp_build_chart.dep_up()
            tmp_build_chart.lint_chart()
            tmp_build_chart.lint_kubeval()

        return target_dir

    @staticmethod
    def build_platforms():
        BuildUtils.logger.info(f"build_platforms")

        build_order = BuildUtils.get_build_order()
        for platform_chart in HelmChart.build_tree:
            HelmChart.create_build_version(chart=platform_chart)
            assert exists(platform_chart.build_chartfile)
            build_platform_chart = HelmChart(chartfile=platform_chart.build_chartfile)
            build_platform_chart.make_package()
            build_platform_chart.push()
            BuildUtils.logger.info(f"{platform_chart.chart_id}: DONE")

        BuildUtils.logger.info("Start container build...")
        container_count = len(build_order)
        for i in range(0, container_count):
            container_id = build_order[i]
            BuildUtils.logger.info("")
            BuildUtils.logger.info(f"container {i}/{container_count}: {container_id}")
            container_to_build = [x for x in BuildUtils.container_images_available if x.tag == container_id]
            if len(container_to_build) == 1:
                container_to_build[0].build()
                container_to_build[0].push()
            else:
                BuildUtils.logger.error(f"{container_id} could not be found in available containers!")
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name="container_build",
                    msg=f"{container_id} could not be found in available containers!",
                    level="FATAL"
                )

        BuildUtils.logger.info("PLATFORM BUILD DONE.")

    @staticmethod
    def generate_platform_build_tree():
        BuildUtils.logger.info(f"generate_platform_build_tree")
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

        HelmChart.build_tree = charts_to_build

        generate_build_graph(HelmChart.build_tree)

        return HelmChart.build_tree

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
