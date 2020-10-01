from shutil import which, copy
import yaml
import json
import os
import getpass
from glob import glob
from argparse import ArgumentParser
from build_helper.charts_build_and_push_all import HelmChart
from build_helper.containers_build_and_push_all import start_container_build
from build_helper.charts_build_and_push_all import init_helm_charts

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
        print("Step: {}".format(log_entry["step"] if "step" in log_entry else "na"))
        print("Message: {}".format(log_entry["message"] if "message" in log_entry else "na"))
        print("-----------------------------------------------------------")

    if "container" in log_entry:
        del log_entry['container']
    log_list[kind].append([log_entry_loglevel, json.dumps(log_entry, indent=4, sort_keys=True)])


if __name__ == '__main__':

    parser = ArgumentParser()
    parser.add_argument("-u", "--username", dest="username", default=None, help="Username")
    parser.add_argument("-p", "--password", dest="password", default=None, required=False, help="Password")
    parser.add_argument("-bo", "--build-only", dest="build_only", default=False, action='store_true', help="Just building the containers and charts -> no pushing")
    parser.add_argument("-co", "--charts-only", dest="charts_only", default=False, action='store_true', help="Just build all helm charts.")
    parser.add_argument("-do", "--docker-only", dest="docker_only", default=False, action='store_true', help="Just build all Docker containers charts.")

    args = parser.parse_args()
    registry_user = args.username
    registry_pwd = args.password
    build_only = args.build_only
    charts_only = args.charts_only
    docker_only = args.docker_only

    kaapana_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.isdir(os.path.join(kaapana_dir, "platforms")):
        print("The dir 'platforms' was not found! -> wrong kaapana_dir? -> exit!")
        print("-----------------------------------------------------------")
        exit(1)

    config_filepath = os.path.join(kaapana_dir, "build-scripts", "build-configuration.yaml")
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

    if "build_mode" not in configuration or (configuration["build_mode"] != "local" and configuration["build_mode"] != "private" and configuration["build_mode"] != "dockerhub"):
        print("-----------------------------------------------------------")
        print("------------------- CONFIGURATION ERROR -------------------")
        print("-----------------------------------------------------------")
        print("Please set the configuration key 'build_mode' to 'local', 'dockerhub', 'private'")
        print("Please adjust the build-configuration.yaml")
        print("Abort")
        exit(1)

    build_mode = configuration["build_mode"]
    print("Build-mode: {}!".format(build_mode))

    build_containers = configuration["build_containers"]
    push_containers = configuration["push_containers"]
    print("build_containers: {}".format(build_containers))
    print("push_containers: {}".format(push_containers))
    
    create_package = configuration["create_package"]
    if build_mode == "local":
        print("local build: Forcing create_package = True !")
        create_package = True
    
    if create_package:
        build_dir = os.path.join(kaapana_dir,"build")
        os.makedirs(build_dir, exist_ok=True)

    build_charts = configuration["build_charts"]
    push_charts = configuration["push_charts"]

    if build_mode == "local" and push_charts:
        print("local build: Forcing push_charts = False !")
        push_charts=False

    if build_mode == "local" and push_containers:
        print("local build: Forcing push_containers = False !")
        push_containers=False
    
    print()
    print("build_charts: {}".format(build_charts))
    print("push_charts: {}".format(push_charts))

    if configuration["http_proxy"] == "":
        http_proxy = os.environ.get("http_proxy", "")

    if http_proxy == "":
        print("no proxy configured...")
        http_proxy = None
    else:
        print("Using http_proxy: {}".format(http_proxy))

    if build_containers and not charts_only:
        print("-----------------------------------------------------------")
        default_container_registry = configuration["default_container_registry"]
        if default_container_registry == "" and build_mode != "local":
            print("No default registry configured!")
            print("Please specify 'default_container_registry' within the build-configuration.json")
            exit(1)
        elif default_container_registry == "" and build_mode == "local":
            default_container_registry = "local"
        else:
            print("Using default_container_registry: {}".format(default_container_registry))
        print("-----------------------------------------------------------")
        default_container_project = configuration["default_container_project"]
        if default_container_project == "":
            print("no default_container_project configured.")
            default_container_project = None
        else:
            print("Using default_container_project: {}".format(default_container_project))
        print("-----------------------------------------------------------")

    default_chart_registry = configuration["default_chart_registry"] if "default_chart_registry" in configuration else ""
    default_chart_project = configuration["default_chart_project"] if "default_chart_project" in configuration else ""
    if not docker_only:
        print("-----------------------------------------------------------")
        default_chart_registry = configuration["default_chart_registry"]
        if default_chart_registry == "":
            print("No default default_chart_registry configured!")
            print("Please specify 'default_chart_registry' within the build-configuration.json")
            exit(1)
        else:
            print("Using default_chart_registry: {}".format(default_chart_registry))
        print("-----------------------------------------------------------")

        if push_charts and (registry_user is None or registry_pwd is None):
            if os.getenv("REGISTRY_USER", None) is None or os.getenv("REGISTRY_PW", None) is None:
                print()
                print("ENVs 'REGISTRY_USER' and 'REGISTRY_PW' not found! ")
                print()

                registry_user = input("User for {}: ".format(default_chart_registry))
                print()
                print("Registry-User: {}".format(registry_user))
                registry_pwd = getpass.getpass("password: ")
            else:
                registry_user = os.getenv("REGISTRY_USER", None)
                registry_pwd = os.getenv("REGISTRY_PW", None)

        default_chart_project = configuration["default_chart_project"]
        if default_chart_project == "":
            print("no default_chart_project configured.")
            default_chart_project = None
        else:
            print("Using default_chart_project: {}".format(default_chart_project))
        print("-----------------------------------------------------------")

    log_level = configuration["log_level"].upper()
    if log_level not in supported_log_levels:
        print("Log level {} not supported.")
        print("Please use 'DEBUG','WARN' or 'ERROR' for log_level in build-configuration.json")
        exit(1)

    log_level = supported_log_levels.index(log_level)

    print("-----------------------------------------------------------")
    if build_containers and not charts_only:
        print("-----------------------------------------------------------")
        print("------------------------ CONTAINER ------------------------")
        print("-----------------------------------------------------------")
        config_list = (kaapana_dir, http_proxy, default_container_registry, default_container_project)
        docker_containers_list, logs = start_container_build(config=config_list)

        for log in logs:
            if supported_log_levels.index(log['loglevel'].upper()) >= log_level:
                print_log_entry(log)
            if log['loglevel'].upper() == "ERROR":
                exit(1)

        i = 0
        for docker_container in docker_containers_list:
            i += 1
            print()
            print("Container: {}".format(docker_container.tag.replace(docker_container.docker_registry, "")[1:]))
            print("{}/{}".format(i, len(docker_containers_list)))
            print()
            try:
                if docker_container.ci_ignore:
                    print('SKIP {}: CI_IGNORE == True!'.format(docker_container.tag.replace(docker_container.docker_registry, "")[1:]))
                    continue
                for log in docker_container.check_prebuild():
                    print_log_entry(log, kind="CONTAINERS")
                    if log['loglevel'].upper() == "ERROR":
                        raise SkipException('SKIP {}: check_prebuild() failed!'.format(log['test']), log=log)

                for log in docker_container.build():
                    print_log_entry(log, kind="CONTAINERS")
                    if log['loglevel'].upper() == "ERROR":
                        raise SkipException('SKIP {}: build() failed!'.format(log['test']), log=log)
                
                if not build_only and push_containers:
                    for log in docker_container.push():
                        print_log_entry(log, kind="CONTAINERS")
                        if log['loglevel'].upper() == "ERROR":
                            raise SkipException('SKIP {}: push() failed!'.format(log['test']), log=log)

            except SkipException as error:
                print("SkipException: {}".format(str(error)))
                continue

    if build_charts and not docker_only:
        print("-----------------------------------------------------------")
        print("------------------------- CHARTS --------------------------")
        print("-----------------------------------------------------------")

        print("Init HelmCharts...")
        init_helm_charts(kaapana_dir=kaapana_dir, chart_registry=default_chart_registry, default_project=default_chart_project)

        print("Start quick_check...")
        for log_entry in HelmChart.quick_check():
            if isinstance(log_entry, dict):
                print_log_entry(log_entry, kind="CHARTS")
            else:
                build_ready_list = log_entry

        if push_charts:
            print("Start check_repos...")
            for log_entry in HelmChart.check_repos(user=registry_user, pwd=registry_pwd):
                print_log_entry(log_entry, kind="CHARTS")
                if log_entry['loglevel'].upper() == "ERROR":
                    print("Could not add repository: {}".format(log_entry["step"]))
                    print("Message: {}".format(log_entry["message"]))
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
                for log_entry in chart.dep_up():
                    print_log_entry(log_entry, kind="CHARTS")
                    if log_entry['loglevel'].upper() == "ERROR":
                        raise SkipException("SKIP {}: dep_up() error!".format(log_entry['test']), log=log_entry)

                for log_entry in chart.lint_chart():
                    print_log_entry(log_entry, kind="CHARTS")
                    if log_entry['loglevel'].upper() == "ERROR":
                        raise SkipException("SKIP {}: dep_up() error!".format(log_entry['test']), log=log_entry)

                for log_entry in chart.lint_kubeval():
                    print_log_entry(log_entry, kind="CHARTS")
                    if log_entry['loglevel'].upper() == "ERROR":
                        raise SkipException("SKIP {}: dep_up() error!".format(log_entry['test']), log=log_entry)

                if "platforms" in chart.chart_dir and create_package:
                    for log_entry in chart.package():
                        print_log_entry(log_entry, kind="CHARTS")
                        if log_entry['loglevel'].upper() == "ERROR":
                            raise SkipException("SKIP {}: package() error!".format(log_entry['test']), log=log_entry)
                        else:
                            packages = glob(os.path.join(os.path.dirname(chart.chart_dir),'*.tgz'))
                            for package in packages:
                                copy(package, build_dir)
                                os.remove(package)

                if not build_only and push_charts:
                    for log_entry in chart.push():
                        print_log_entry(log_entry, kind="CHARTS")
                        if log_entry['loglevel'].upper() == "ERROR":
                            raise SkipException("SKIP {}: dep_up() error!".format(log_entry['test']), log=log_entry)

            except SkipException as error:
                print("SkipException: {}".format(str(error)))
                continue

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
    print("")
    print("")
    print("-----------------------------------------------------------")
    print("-------------------------- DONE ---------------------------")
    print("-----------------------------------------------------------")
