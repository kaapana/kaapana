from shutil import which
import yaml
import json
import os
import getpass
from containers_build_and_push_all import start_container_build
from charts_build_and_push_all import init_helm_charts
from charts_build_and_push_all import HelmChart


class SkipException(Exception):
    """Exception raised for errors within the build-process.

    Attributes:
        reason  -- reason why the container was skipped for the build process
    """

    def __init__(self, reason, log=None):
        self.reason = reason
        self.log = log
        super().__init__(self.reason)

    def __str__(self):
        if self.log is not None:
            return self.reason + "\n" +json.dumps(self.log, indent=4, sort_keys=True)
        else:
            return self.reason


def print_log_entry(log_entry):
    if supported_log_levels.index(log_entry['loglevel'].upper()) >= log_level:
        print("-----------------------------------------------------------")
        print("Log: {}".format(log_entry["test"]))
        print("Step: {}".format(log_entry["step"]))
        print("Message: {}".format(log_entry["message"]))
        print("-----------------------------------------------------------")
        # print(json.dumps(log_entry_copy, indent=4, sort_keys=True))


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

build_containers = configuration["build_containers"]
print("build_containers: {}".format(build_containers))
build_charts = configuration["build_charts"]
print("build_charts: {}".format(build_charts))


if configuration["http_proxy"] == "":
    http_proxy = os.environ.get("http_proxy", "")

if http_proxy == "":
    print("no proxy configured...")
    http_proxy = None
else:
    print("Using http_proxy: {}".format(http_proxy))

if build_containers:
    print("-----------------------------------------------------------")
    default_container_registry = configuration["default_container_registry"]
    if default_container_registry == "":
        print("No default registry configured!")
        print("Please specify 'default_container_registry' within the build-configuration.json")
        exit(1)
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

if build_charts:
    print("-----------------------------------------------------------")
    default_chart_registry = configuration["default_chart_registry"]
    if default_chart_registry == "":
        print("No default default_chart_registry configured!")
        print("Please specify 'default_chart_registry' within the build-configuration.json")
        exit(1)
    else:
        print("Using default_chart_registry: {}".format(default_chart_registry))
    print("-----------------------------------------------------------")

    if os.getenv("REGISTRY_USER", None) is None or os.getenv("REGISTRY_PW", None) is None:
        print()
        print("ENVs 'REGISTRY_USER' and 'REGISTRY_PW' not found! ")
        print()
        registry_user = input("Registry user: ")
        print()
        print("User: {}".format(registry_user))
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

supported_log_levels = ["DEBUG", "WARN", "ERROR"]
log_level = configuration["log_level"].upper()
if log_level not in supported_log_levels:
    print("Log level {} not supported.")
    print("Please use 'DEBUG','WARN' or 'ERROR' for log_level in build-configuration.json")
    exit(1)

log_level = supported_log_levels.index(log_level)

print("-----------------------------------------------------------")
if build_containers:
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

    error_list = []
    
    i = 0
    for docker_container in docker_containers_list:
        i += 1
        print()
        print("Container: {}".format(docker_container.tag.replace(docker_container.docker_registry, "")[1:]))
        print("{}/{}".format(i,len(docker_containers_list)))
        print()
        try:
            if docker_container.ci_ignore:
                print('SKIP {}: CI_IGNORE == True!'.format(docker_container.tag.replace(docker_container.docker_registry, "")[1:]))
                continue
            for log in docker_container.check_prebuild():
                print_log_entry(log)
                if log['loglevel'].upper() == "ERROR":
                    raise SkipException('SKIP {}: check_prebuild() failed!'.format(log['test']),log=log)

            for log in docker_container.build():
                print_log_entry(log)
                if log['loglevel'].upper() == "ERROR":
                    raise SkipException('SKIP {}: build() failed!'.format(log['test']),log=log)

            for log in docker_container.push():
                print_log_entry(log)
                if log['loglevel'].upper() == "ERROR":
                    raise SkipException('SKIP {}: push() failed!'.format(log['test']),log=log)

        except SkipException as error:
            print("SkipException: {}".format(str(error)))
            error_list.append(str(error))
            continue

    print("-----------------------------------------------------------")
    if len(error_list) > 0:
        print("--------------------- CONTAINER ERROR ---------------------")
        for error in error_list:
            print(error)
            print("-----------------------------------------------------------")

error_list = []
if build_charts:
    print("-----------------------------------------------------------")
    print("------------------------- CHARTS --------------------------")
    print("-----------------------------------------------------------")

    print("Init HelmCharts...")
    init_helm_charts(kaapana_dir=kaapana_dir, chart_registry=default_chart_registry, default_project=default_chart_project)

    print("Start quick_check...")
    for log_entry in HelmChart.quick_check():
        if isinstance(log_entry, dict):
            print_log_entry(log_entry)
            if log_entry['loglevel'].upper() == "ERROR":
                print("Quick-Check failed: {}".format(log_entry["step"]))
                print("Message: {}".format(log_entry["message"]))
                print(json.dumps(log_entry["log"], indent=4, sort_keys=True))
        else:
            build_ready_list = log_entry

    print("Start check_repos...")
    for log_entry in HelmChart.check_repos(user=registry_user, pwd=registry_pwd):
        print_log_entry(log_entry)
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
            print("{}/{}".format(i,len(build_ready_list)))
            print()
            chart.remove_tgz_files()
            for log_entry in chart.dep_up():
                print_log_entry(log_entry)
                if log_entry['loglevel'].upper() == "ERROR":
                    raise SkipException("SKIP {}: dep_up() error!".format(log_entry['test']),log=log_entry)

            for log_entry in chart.lint_chart():
                print_log_entry(log_entry)
                if log_entry['loglevel'].upper() == "ERROR":
                    raise SkipException("SKIP {}: dep_up() error!".format(log_entry['test']),log=log_entry)

            for log_entry in chart.lint_kubeval():
                print_log_entry(log_entry)
                if log_entry['loglevel'].upper() == "ERROR":
                    raise SkipException("SKIP {}: dep_up() error!".format(log_entry['test']),log=log_entry)

            for log_entry in chart.push():
                print_log_entry(log_entry)
                if log_entry['loglevel'].upper() == "ERROR":
                    raise SkipException("SKIP {}: dep_up() error!".format(log_entry['test']),log=log_entry)

        except SkipException as error:
            print("SkipException: {}".format(str(error)))
            error_list.append(str(error))
            continue

    print("-----------------------------------------------------------")
    if len(error_list) > 0:
        print("---------------------- CHART ERRORS -----------------------")
        for error in error_list:
            print(error)
            print("-----------------------------------------------------------")


print("-----------------------------------------------------------")
print("-------------------------- DONE ---------------------------")
print("-----------------------------------------------------------")
