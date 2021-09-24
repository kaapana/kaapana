#!/usr/bin/env python3
from genericpath import exists
from shutil import which, copy, rmtree
import yaml
import json
import os
import getpass
from glob import glob
from time import time
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from argparse import ArgumentParser
from build_helper.charts_build_and_push_all import HelmChart
from build_helper.containers_build_and_push_all import start_container_build, container_registry_login
from build_helper.charts_build_and_push_all import init_helm_charts, helm_registry_login

os.environ["HELM_EXPERIMENTAL_OCI"] = "1"
log_list = {
    "CONTAINERS": [],
    "CHARTS": [],
    "OTHER": []
}
supported_log_levels = ["DEBUG", "WARN", "ERROR"]


class SkipException(Exception):
    """Exception raised for errors within the build-process.

    Attributes:
        reason  -- reason why the container was skipped for the build process
    """

    def __init__(self, reason, log=None):
        self.reason = reason
        if "container" in log:
            del log['container']
        self.log = log
        super().__init__(self.reason)

    def __str__(self):
        if self.log is not None:
            return self.reason + "\n" + json.dumps(self.log, indent=4, sort_keys=True)
        else:
            return self.reason


def print_log_entry(log_entry, kind="OTHER"):
    log_entry_loglevel = log_entry['loglevel'].upper()
    if supported_log_levels.index(log_entry_loglevel) >= log_level:
        print("-----------------------------------------------------------")
        print("Log: {}".format(log_entry["test"]))
        print("Step: {}".format(log_entry["step"] if "step" in log_entry else "N/A"))
        print("Message: {}".format(log_entry["message"] if "message" in log_entry else "N/A"))
        print("-----------------------------------------------------------")

    if "container" in log_entry:
        del log_entry['container']
    log_list[kind].append([log_entry_loglevel, json.dumps(log_entry, indent=4, sort_keys=True)])


if __name__ == '__main__':

    parser = ArgumentParser()
    parser.add_argument("-c", "--config", dest="config_filepath", default=None, help="Path the the build-configuration.yaml")
    parser.add_argument("-u", "--username", dest="username", default=None, help="Username")
    parser.add_argument("-p", "--password", dest="password", default=None, required=False, help="Password")
    parser.add_argument("-bo", "--build-only", dest="build_only", default=False, action='store_true', help="Just building the containers and charts -> no pushing")
    parser.add_argument("-iso", "--installer-scripts-only", dest="installer_scripts_only", default=False, action='store_true', help="Just build all installation scripts.")
    parser.add_argument("-co", "--charts-only", dest="charts_only", default=False, action='store_true', help="Just build all helm charts.")
    parser.add_argument("-do", "--docker-only", dest="docker_only", default=False, action='store_true', help="Just build all Docker containers charts.")
    parser.add_argument("-dk", "--disable-kubeval", dest="disable_kubeval", default=False, action='store_true', help="Disable helm kubeval linting.")
    parser.add_argument("-bd", "--build-dir", dest="build_dir", default=None, help="base dir to search for containers and charts.")

    args = parser.parse_args()
    registry_user = args.username
    registry_pwd = args.password
    build_only = args.build_only
    charts_only = args.charts_only
    docker_only = args.docker_only
    installer_scripts_only = args.installer_scripts_only
    config_filepath = args.config_filepath
    disable_kubeval = args.disable_kubeval
    build_dir = args.build_dir

    kaapana_dir = build_dir if build_dir is not None else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.isdir(os.path.join(kaapana_dir, "platforms")):
        print("The dir 'platforms' was not found! -> wrong kaapana_dir? -> exit!")
        print("-----------------------------------------------------------")
        exit(1)

    config_filepath = config_filepath if config_filepath is not None else os.path.join(kaapana_dir, "build-scripts", "build-configuration.yaml")
    if not os.path.isfile(config_filepath):
        print("The build-configuration.yaml file was not found at: {}".format(config_filepath))
        print("-----------------------------------------------------------")
        exit(1)
    print("-----------------------------------------------------------")
    print("--------------- loading build-configuration ---------------")
    print("-----------------------------------------------------------")

    with open(config_filepath, 'r') as stream:
        try:
            configuration = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    build_installer_scripts = False if (charts_only or docker_only) else True

    build_containers = False if (charts_only or installer_scripts_only) else configuration["build_containers"]
    push_containers = False if (charts_only or installer_scripts_only) else configuration["push_containers"]
    push_containers = False if build_only else push_containers
    push_dev_only = configuration["push_dev_containers_only"] if "push_dev_containers_only" in configuration else False
    default_container_registry = configuration["default_container_registry"] if "default_container_registry" in configuration else ""

    create_package = configuration["create_package"]
    if default_container_registry == "" and not create_package:
        print("local build: Forcing create_package = True !")
        create_package = True

    build_dir = os.path.join(kaapana_dir, "build")
    if exists(build_dir):
        rmtree(build_dir)
    if create_package:
        os.makedirs(build_dir, exist_ok=True)

    build_charts = False if (docker_only or installer_scripts_only) else configuration["build_charts"]
    push_charts = False if (docker_only or installer_scripts_only)  else configuration["push_charts"]
    push_charts = False if build_only else push_charts

    if default_container_registry == "" and push_charts:
        print("local build: Forcing push_charts = False !")
        push_charts = False

    if default_container_registry == "" and push_containers:
        print("local build: Forcing push_containers = False !")
        push_containers = False

    print()
    print("build_containers: {}".format(build_containers))
    print("push_containers: {}".format(push_containers))
    print()
    print("build_charts: {}".format(build_charts))
    print("push_charts: {}".format(push_charts))

    if configuration["http_proxy"] == "":
        http_proxy = os.environ.get("http_proxy", "")
    else:
        http_proxy = configuration["http_proxy"]

    if http_proxy == "":
        print("no proxy configured...")
        http_proxy = None
    else:
        print(f"Using http_proxy: {http_proxy}")

    if default_container_registry == "":
        default_container_registry = "local"
    print("-----------------------------------------------------------")
    print("Using default_container_registry: {}".format(default_container_registry))
    print("-----------------------------------------------------------")

    if push_charts or push_containers:
        if registry_user is None or registry_pwd is None:
            if os.getenv("REGISTRY_USER", None) is None or os.getenv("REGISTRY_PW", None) is None:
                print()
                print("ENVs 'REGISTRY_USER' and 'REGISTRY_PW' not found! ")
                print()

                registry_user = input("User for {}: ".format(default_container_registry))
                print()
                print("Registry-User: {}".format(registry_user))
                registry_pwd = getpass.getpass("password: ")
            else:
                print("Using ENV registry-credentials ...")
                registry_user = os.getenv("REGISTRY_USER", None)
                registry_pwd = os.getenv("REGISTRY_PW", None)

        if push_containers:
            container_registry_login(container_registry=default_container_registry, username=registry_user, password=registry_pwd)
        if push_charts:
            helm_registry_login(container_registry=default_container_registry, username=registry_user, password=registry_pwd)

    log_level = configuration["log_level"].upper()
    if log_level not in supported_log_levels:
        print("Log level {} not supported.")
        print("Please use 'DEBUG','WARN' or 'ERROR' for log_level in build-configuration.json")
        exit(1)

    log_level = supported_log_levels.index(log_level)

    startTime = time()
    print("-----------------------------------------------------------")


    if build_installer_scripts:
        print("-----------------------------------------------------------")
        print("-------------------- Installer scripts --------------------")
        print("-----------------------------------------------------------")
        platforms_dir = Path(kaapana_dir) / "platforms"
        print(str(platforms_dir))
        file_loader = FileSystemLoader(str(platforms_dir)) # directory of template file
        env = Environment(loader=file_loader)
        for config_path in platforms_dir.rglob('installer_config.yaml'):
            platform_params = yaml.load(open(config_path), Loader=yaml.FullLoader)
            print(f'Creating installer script for {platform_params["project_name"]}')
            template = env.get_template('install_platform_template.sh') # load template file

            output = template.render(**platform_params)
            with open (config_path.parents[0] / 'install_platform.sh', 'w') as rsh:
                rsh.write(output)


    if build_charts:
        print("-----------------------------------------------------------")
        print("------------------------- CHARTS --------------------------")
        print("-----------------------------------------------------------")

        print("Init HelmCharts...")
        init_helm_charts(kaapana_dir=kaapana_dir, chart_registry=default_container_registry)

        print("Start quick_check...")
        # for log_entry in HelmChart.quick_check(push_charts_to_docker):
        for log_entry in HelmChart.quick_check():
            if isinstance(log_entry, dict):
                print_log_entry(log_entry, kind="CHARTS")
            else:
                all_charts = log_entry

        print("Creating build order ...")

        tries = 0
        max_tries = 5
        build_ready_list = []
        not_ready_list = all_charts.copy()
        while len(not_ready_list) > 0 and tries < max_tries:
            tries += 1
            all_ready = True
            not_ready_list_tmp = []
            for chart in not_ready_list:
                chart.dependencies_ready = True
                for dependency in chart.dependencies:
                    ready_charts = [ready_chart for ready_chart in build_ready_list if ready_chart.name == dependency["name"] and ready_chart.version == dependency["version"]]
                    if len(ready_charts) == 0:
                        chart.dependencies_ready = False
                        break
                if chart.dependencies_ready:
                    build_ready_list.append(chart)
                else:
                    not_ready_list_tmp.append(chart)

            not_ready_list = not_ready_list_tmp

        if tries >= max_tries:
            print("#########################################################################")
            print("")
            print("                    Issue with dependencies!")
            print("")
            print("#########################################################################")
            print("")
            for chart in not_ready_list:
                print(f"Missing dependencies for chart: {chart.name}")
                print("")
            print("")
            exit(1)

        print("Start build- and push-process ...")
        i = 0
        for chart in build_ready_list:
            i += 1
            try:
                print()
                print("chart: {}".format(chart.chart_id))
                print("{}/{}".format(i, len(build_ready_list)))
                print()
                chart.remove_tgz_files()
                print("dep up ...")
                for log_entry in chart.dep_up():
                    print_log_entry(log_entry, kind="CHARTS")
                    if log_entry['loglevel'].upper() == "ERROR":
                        raise SkipException("SKIP {}: dep_up() error!".format(log_entry['test']), log=log_entry)

                print("linting ...")
                for log_entry in chart.lint_chart():
                    print_log_entry(log_entry, kind="CHARTS")
                    if log_entry['loglevel'].upper() == "ERROR":
                        raise SkipException("SKIP {}: lint_chart() error!".format(log_entry['test']), log=log_entry)
                
                if not disable_kubeval:
                    print("kubeval ...")
                    for log_entry in chart.lint_kubeval():
                        print_log_entry(log_entry, kind="CHARTS")
                        if log_entry['loglevel'].upper() == "ERROR":
                            raise SkipException("SKIP {}: lint_kubeval() error!".format(log_entry['test']), log=log_entry)

                if "platforms" in chart.chart_dir and not chart.local_only:
                    if push_charts is True:
                        print("saving chart ...")
                        for log_entry in chart.chart_save():
                            print_log_entry(log_entry, kind="CHARTS")
                            if log_entry['loglevel'].upper() == "ERROR":
                                raise SkipException("SKIP {}: chart_save() error!".format(log_entry['test']), log=log_entry)

                        print("pushing chart ...")
                        for log_entry in chart.chart_push():
                            print_log_entry(log_entry, kind="CHARTS")
                            if log_entry['loglevel'].upper() == "ERROR":
                                raise SkipException("SKIP {}: chart_push() error!".format(log_entry['test']), log=log_entry)
                    if create_package:
                        print("platform-chart! -> exporting package ...")
                        for log_entry in chart.package():
                            print_log_entry(log_entry, kind="CHARTS")
                            if log_entry['loglevel'].upper() == "ERROR":
                                raise SkipException("SKIP {}: package() error!".format(log_entry['test']), log=log_entry)
                            else:
                                packages = glob(os.path.join(os.path.dirname(chart.chart_dir), '*.tgz'))
                                for package in packages:
                                    copy(package, build_dir)
                                    os.remove(package)

                print()
                print()
            except SkipException as error:
                print("SkipException: {}".format(str(error)))
                continue
            
    if build_containers:
        print("-----------------------------------------------------------")
        print("------------------------ CONTAINER ------------------------")
        print("-----------------------------------------------------------")
        config_list = (kaapana_dir, http_proxy, default_container_registry)
        docker_containers_list, logs = start_container_build(config=config_list)

        for log in logs:
            if supported_log_levels.index(log['loglevel'].upper()) >= log_level:
                print_log_entry(log, kind="CONTAINERS")
            if log['loglevel'].upper() == "ERROR":
                exit(1)

        i = 0
        for docker_container in docker_containers_list:
            i += 1
            print()
            print("Container: {}".format(docker_container.tag.replace(docker_container.container_registry, "")[1:]))
            print("{}/{}".format(i, len(docker_containers_list)))
            print()
            try:
                if docker_container.ci_ignore:
                    print('SKIP {}: CI_IGNORE == True!'.format(docker_container.tag.replace(docker_container.container_registry, "")[1:]))
                    continue
                for log in docker_container.check_prebuild():
                    print_log_entry(log, kind="CONTAINERS")
                    if log['loglevel'].upper() == "ERROR":
                        raise SkipException('SKIP {}: check_prebuild() failed!'.format(log['test']), log=log)

                for log in docker_container.build():
                    print_log_entry(log, kind="CONTAINERS")
                    if log['loglevel'].upper() == "ERROR":
                        raise SkipException('SKIP {}: build() failed!'.format(log['test']), log=log)

                if push_containers:
                    if push_dev_only and not docker_container.dev:
                        print(f"Skipping push for {docker_container.tag.split('/')[-1]} -> no dev container")
                        continue

                    for log in docker_container.push():
                        print_log_entry(log, kind="CONTAINERS")
                        if log['loglevel'].upper() == "ERROR":
                            raise SkipException('SKIP {}: push() failed!'.format(log['test']), log=log)

            except SkipException as error:
                print("SkipException: {}".format(str(error)))
                continue

    print("-----------------------------------------------------------")
    if len(log_list["CHARTS"]) > 0:
        print("")
        print("-----------------------------------------------------------")
        print("--------------------- Chart issues: -----------------------")
        print("-----------------------------------------------------------")
        print("")
        for log in log_list["CHARTS"]:
            if supported_log_levels.index(log[0]) >= log_level:
                print(log[1])
                print("-----------------------------------------------------------")
                print()
    print("-----------------------------------------------------------")

    if len(log_list["CONTAINERS"]) > 0:
        print("")
        print("-----------------------------------------------------------")
        print("------------------- Container issues: ---------------------")
        print("-----------------------------------------------------------")
        print("")
        for log in log_list["CONTAINERS"]:
            if supported_log_levels.index(log[0]) >= log_level:
                print(log[1])
                print("-----------------------------------------------------------")
                print()


    hours, rem = divmod(time()-startTime, 3600)
    minutes, seconds = divmod(rem, 60)
    print("-----------------------------------------------------------")
    print("------------------ TIME NEEDED: {:0>2}:{:0>2}:{:0>2} -----------------".format(int(hours), int(minutes), int(seconds)))
    print("-----------------------------------------------------------")
    print("-------------------------- DONE ---------------------------")
    print("-----------------------------------------------------------")
