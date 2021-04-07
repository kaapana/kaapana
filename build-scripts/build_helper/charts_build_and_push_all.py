#!/usr/bin/env python3
import sys
import yaml
import glob
import os
import json
from subprocess import PIPE, run

from os.path import join, dirname, basename, exists, isfile, isdir
from shutil import copyfile
from argparse import ArgumentParser
from time import time
from pathlib import Path

suite_tag = "Helm Charts"


def get_timestamp():
    return str(int(time() * 1000))


def helm_registry_login(container_registry, username, password):
    print(f"-> Helm registry-login: {container_registry}")
    command = ["helm", "registry", "login", container_registry, "--username", username, "--password", password]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=5)

    if output.returncode != 0:
        print("Something went wrong!")
        print(f"Helm couldn't login into registry {container_registry}")
        print(f"Message: {output.stdout}")
        print(f"Error:   {output.stderr}")
        exit(1)


def check_helm_installed():
    command = ["helm", "push", "--help"]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=5)

    if output.returncode != 0 or "The Kubernetes package manager" in output.stdout:
        print("Helm ist not installed correctly!")
        print("Make sure Helm > v3 and the 'push'-plugin is installed!")
        print("hint: helm plugin install https://github.com/chartmuseum/helm-push")
        exit(1)

    command = ["helm", "kubeval", "--help"]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=5)
    if output.returncode != 0 or "The Kubernetes package manager" in output.stdout:
        print("Helm kubeval ist not installed correctly!")
        print("Make sure Helm kubeval-plugin is installed!")
        print("hint: helm plugin install https://github.com/instrumenta/helm-kubeval")
        exit(1)


def make_log(std_out, std_err):
    std_out = std_out.split("\n")[-100:]
    log = {}
    len_std = len(std_out)
    for i in range(0, len_std):
        log[i] = std_out[i]

    std_err = std_err.split("\n")
    for err in std_err:
        if err != "":
            len_std += 1
            log[len_std] = "ERROR: {}".format(err)

    return log


class HelmChart:
    registries_needed = []
    docker_containers_used = {}
    max_tries = 3
    kaapana_dir = None
    default_registry = None

    def __eq__(self, other):
        return "{}:{}".format(self.name, self.version) == "{}:{}".format(other.name, other.version)

    def __init__(self, chartfile):
        self.name = None
        self.version = None
        self.nested = False
        self.chart_id = None
        self.ignore_linting = False
        self.log_list = []
        self.chartfile = chartfile
        self.local_only = False
        self.dev_version = False
        self.dependencies = []
        self.dependencies_ready = False

        if not isfile(chartfile):
            print("ERROR: Chartfile not found.")
            exit(1)

        with open(chartfile) as f:
            read_file = f.readlines()
            read_file = [x.strip() for x in read_file]

            for line in read_file:
                if "name:" in line:
                    self.name = line.split(": ")[1].strip()
                elif "version:" in line:
                    self.version = line.split(": ")[1].strip().replace('"', '').replace("'", '')
                elif "ignore_linting:" in line:
                    self.ignore_linting = line.split(": ")[1].strip().lower() == "true"

        if self.name is not None and self.version is not None:
            self.path = self.chartfile
            self.chart_dir = dirname(chartfile)

            if "-vdev" in self.version:
                self.local_only = True

            if "/deps/" in chartfile:
                self.local_only = True
                # self.repo = f"file://deps/{self.name}"

            self.chart_id = f"{self.name}:{self.version}"

            if not self.nested:
                for log_entry in self.check_dependencies():
                    self.log_list.append(log_entry)
                log_entry = {
                    "suite": suite_tag,
                    "test": "{}:{}".format(self.name, self.version),
                    "step": "Extract Chart Infos",
                    "loglevel": "DEBUG",
                    "timestamp": get_timestamp(),
                    "log": "",
                    "message": "Chart added successfully.",
                    "rel_file": self.chart_dir,
                }
                self.log_list.append(log_entry)

            self.check_container_use()

        else:
            log_entry = {
                "suite": suite_tag,
                "test": "{}".format(self.name if self.name is not None else chartfile),
                "step": "Extract Chart Infos",
                "log": "",
                "loglevel": "ERROR",
                "timestamp": get_timestamp(),
                "message": "Could not extract all infos from chart.",
                "rel_file": chartfile,
            }
            self.log_list.append(log_entry)

            print("")
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("")
            print("ERROR: Cound not extract all infos from chart...")
            print("name: {}".format(self.name if self.name is not None else chartfile))
            print("version: {}".format(self.version if self.name is not None else ""))
            print("file: {}".format(self.chartfile if self.name is not None else ""))
            print("")
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("")

    def check_dependencies(self):
        log_list = []
        dependencie_count_all = 0
        dependencie_count_found = 0
        for requirements_file in Path(self.chart_dir).rglob('requirements.yaml'):
            requirements_yaml = {}
            with open(str(requirements_file)) as f:
                requirements_yaml = yaml.safe_load(f)

            if requirements_yaml == None or "dependencies" not in requirements_yaml or requirements_yaml["dependencies"] == None:
                continue
            dependencie_count_all += len(requirements_yaml["dependencies"])
            for dependency in requirements_yaml["dependencies"]:
                check_chart_yaml = None
                if dependency["repository"].startswith('file://deps'):
                    check_chart_yaml = join(self.chart_dir, dependency["repository"].replace("file://", ""), "Chart.yaml")
                elif dependency["repository"].startswith('file://'):
                    dep_dir = str(requirements_file)
                    for i in range(0, dependency["repository"].count("../")+1):
                        dep_dir = dirname(dep_dir)
                    check_chart_yaml = join(dep_dir, dependency["repository"].replace("file://", "").replace("../", ""), "Chart.yaml")
                else:
                    log_entry = {
                        "suite": suite_tag,
                        "test": self.name,
                        "step": "Check Dependencies",
                        "log": {"Missing dependency": dependency["name"]},
                        "loglevel": "WARN",
                        "timestamp": get_timestamp(),
                        "message": f"{self.chart_dir}: Found non file-based dependency!",
                        "rel_file": "",
                    }
                    log_list.append(log_entry)
                    continue

                if check_chart_yaml != None:
                    if not isfile(check_chart_yaml):
                        log_entry = {
                            "suite": suite_tag,
                            "test": self.name,
                            "step": "Check Dependencies",
                            "log": {"Missing dependency": dependency["name"]},
                            "loglevel": "ERROR",
                            "timestamp": get_timestamp(),
                            "message": f"{self.chart_dir}: Specified file-dependency was not found @{check_chart_yaml} !",
                            "rel_file": "",
                        }
                        log_list.append(log_entry)
                        continue

                    chart_content = None
                    with open(check_chart_yaml, 'r') as stream:
                        chart_content = yaml.safe_load(stream)
                    if chart_content["version"] != dependency["version"]:
                        log_entry = {
                            "suite": suite_tag,
                            "test": self.name,
                            "step": "Check Dependencies",
                            "log": {"Missing dependency": dependency["name"]},
                            "loglevel": "ERROR",
                            "timestamp": get_timestamp(),
                            "message": f"{self.chart_dir}: Specified file-dependency wrong version speciefied {chart_content['version']} found {dependency['version']} !",
                            "rel_file": "",
                        }
                        log_list.append(log_entry)
                        continue
                    else:
                        dependencie_count_found += 1

            self.dependencies.extend(requirements_yaml["dependencies"])

            log_entry = {
                "suite": suite_tag,
                "test": f"{self.name}:{self.version}",
                "step": "Requirements",
                "loglevel": "DEBUG",
                "timestamp": get_timestamp(),
                "log": "",
                "message": "Requirements extracted successfully.",
                "rel_file": self.chart_dir,
            }
            log_list.append(log_entry)
            print(f"{self.name}: found {dependencie_count_found}/{dependencie_count_all} dependencies.")

            if dependencie_count_found != dependencie_count_all:
                log_entry = {
                    "suite": suite_tag,
                    "test": f"{self.name}:{self.version}",
                    "step": "Check Dependencies",
                    "loglevel": "ERROR",
                    "timestamp": get_timestamp(),
                    "log": "",
                    "message": f"{self.chart_dir}: Issue with dependencies!",
                    "rel_file": self.chart_dir,
                }
                log_list.append(log_entry)

        return log_list

    def check_container_use(self):
        template_dirs = (f"{self.chart_dir}/templates/*.yaml", f"{self.chart_dir}/deps/**/templates.yaml")  # the tuple of file types
        files_grabbed = []
        for template_dir in template_dirs:
            files_grabbed.extend(glob.glob(template_dir))
        for yaml_file in files_grabbed:
            with open(yaml_file, "r") as yaml_content:
                for line in yaml_content:
                    line = line.rstrip()
                    if "image:" in line:
                        line = line.split("image:")
                        if "#" in line[0]:
                            print("Commented -> skip")
                            continue
                        elif "}}" in line[1]:
                            docker_container = line[1].split(" }}/")[-1].lower()
                        elif line[1].count("/") == 2:
                            docker_container = line[1].split("/")[-1].lower()
                        else:
                            print("Issue with image line in template-yaml!")
                            continue
                        if docker_container not in HelmChart.docker_containers_used.keys():
                            HelmChart.docker_containers_used[docker_container] = yaml_file

    def dep_up(self, chart_dir=None, log_list=[]):
        if chart_dir is None:
            chart_dir = self.chart_dir
            log_list = []

        dep_charts = join(chart_dir, "charts")
        if isdir(dep_charts):
            for item in os.listdir(dep_charts):
                path = join(dep_charts, item)
                if isdir(path):
                    log_list = self.dep_up(chart_dir=path, log_list=log_list)

        os.chdir(chart_dir)
        try_count = 0
        command = ["helm", "dep", "up"]

        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60)
        while output.returncode != 0 and try_count < HelmChart.max_tries:
            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60)
            try_count += 1
        log = make_log(std_out=output.stdout, std_err=output.stderr)

        if output.returncode != 0:
            log_entry = {
                "suite": suite_tag,
                "test": "{}:{}".format(self.name, self.version),
                "step": "Helm dep up",
                "log": log,
                "loglevel": "ERROR",
                "timestamp": get_timestamp(),
                "message": "repo update failed: {}".format(chart_dir),
                "rel_file": chart_dir,

            }

        else:
            log_entry = {
                "suite": suite_tag,
                "test": "{}:{}".format(self.name, self.version),
                "step": "Helm dep up",
                "log": "",
                "loglevel": "DEBUG",
                "timestamp": get_timestamp(),
                "message": "Dependencies have been successfully updated",
                "rel_file": chart_dir,
            }

        log_list.append(log_entry)
        return log_list

    def remove_tgz_files(self):
        glob_path = '{}/charts'.format(self.chart_dir)
        for path in Path(glob_path).rglob('*.tgz'):
            os.remove(path)

        requirements_lock = '{}/requirements.lock'.format(self.chart_dir)
        if exists(requirements_lock):
            os.remove(requirements_lock)

    def lint_chart(self):
        if self.ignore_linting:
            log_entry = {
                "suite": suite_tag,
                "test": "{}:{}".format(self.name, self.version),
                "step": "Helm lint",
                "log": "",
                "loglevel": "DEBUG",
                "timestamp": get_timestamp(),
                "message": "ignore_linting == true -> Helm lint was skipped!",
                "rel_file": self.path,
            }
        else:
            os.chdir(self.chart_dir)
            command = ["helm", "lint"]
            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=20)
            log = make_log(std_out=output.stdout, std_err=output.stderr)

            if output.returncode != 0:
                log_entry = {
                    "suite": suite_tag,
                    "test": "{}:{}".format(self.name, self.version),
                    "step": "Helm lint",
                    "log": log,
                    "loglevel": "ERROR",
                    "timestamp": get_timestamp(),
                    "message": "Helm lint failed: {}".format(self.path),
                    "rel_file": self.path,
                    "test_done": True,
                }
            else:
                log_entry = {
                    "suite": suite_tag,
                    "test": "{}:{}".format(self.name, self.version),
                    "step": "Helm lint",
                    "log": "",
                    "loglevel": "DEBUG",
                    "timestamp": get_timestamp(),
                    "message": "Helm lint was successful!",
                    "rel_file": self.path,
                }

        yield log_entry

    def lint_kubeval(self):
        os.chdir(self.chart_dir)
        command = ["helm", "kubeval", "--ignore-missing-schemas", "."]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=20)
        log = make_log(std_out=output.stdout, std_err=output.stderr)

        if output.returncode != 0 and "A valid hostname" not in output.stderr:
            print(json.dumps(log, indent=4, sort_keys=True))
            log_entry = {
                "suite": suite_tag,
                "test": "{}:{}".format(self.name, self.version),
                "step": "Helm kubeval",
                "log": log,
                "loglevel": "ERROR",
                "timestamp": get_timestamp(),
                "message": "Kubeval failed: {}".format(self.path),
                "rel_file": self.path,
                "test_done": True,
            }
        else:
            log_entry = {
                "suite": suite_tag,
                "test": "{}:{}".format(self.name, self.version),
                "step": "Helm kubeval",
                "log": "",
                "loglevel": "DEBUG",
                "timestamp": get_timestamp(),
                "message": "Kubeval was successful!",
                "rel_file": self.path,
            }

        yield log_entry

    def package(self):
        os.chdir(dirname(self.chart_dir))
        command = ["helm", "package", self.name]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60)
        log = make_log(std_out=output.stdout, std_err=output.stderr)
        if output.returncode != 0 or "The Kubernetes package manager" in output.stdout:
            log_entry = {
                "suite": suite_tag,
                "test": "{}:{}".format(self.name, self.version),
                "step": "Helm package",
                "log": log,
                "loglevel": "ERROR",
                "timestamp": get_timestamp(),
                "message": "package failed: {}".format(self.name),
                "rel_file": self.path,
                "test_done": True,
            }
            yield log_entry

        else:
            log_entry = {
                "suite": suite_tag,
                "test": "{}:{}".format(self.name, self.version),
                "step": "Helm package",
                "log": log,
                "loglevel": "DEBUG",
                "timestamp": get_timestamp(),
                "message": "Chart package successfully!",
                "rel_file": self.path,
                "test_done": True,
            }
            yield log_entry

    def chart_push(self):
        if not (self.name.endswith('chart') or self.name.endswith('workflow')):
            log_entry = {
                "suite": suite_tag,
                "test": "{}:{}".format(self.name, self.version),
                "step": "Helm push chart to docker",
                "log": "",
                "loglevel": "ERROR",
                "timestamp": get_timestamp(),
                "message": "Chart push failed: {} due to name error. Name of chart has to end with -chart or -workflow!".format(self.name),
                "rel_file": self.path,
                "test_done": True,
            }
            yield log_entry
        else:
            os.chdir(dirname(self.chart_dir))
            try_count = 0

            command = ["helm", "chart", "push", f"{HelmChart.default_registry}/{self.name}:{self.version}"]
            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60)
            while output.returncode != 0 and try_count < HelmChart.max_tries:
                print("Error push -> try: {}".format(try_count))
                output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60)
                try_count += 1
            log = make_log(std_out=output.stdout, std_err=output.stderr)

            if output.returncode != 0 or "The Kubernetes package manager" in output.stdout:
                log_entry = {
                    "suite": suite_tag,
                    "test": "{}:{}".format(self.name, self.version),
                    "step": "Helm push chart to docker",
                    "log": log,
                    "loglevel": "ERROR",
                    "timestamp": get_timestamp(),
                    "message": "push failed: {}".format(self.name),
                    "rel_file": self.path,
                    "test_done": True,
                }
                yield log_entry

            else:
                log_entry = {
                    "suite": suite_tag,
                    "test": "{}:{}".format(self.name, self.version),
                    "step": "Helm push",
                    "log": log,
                    "loglevel": "DEBUG",
                    "timestamp": get_timestamp(),
                    "message": "Chart pushed successfully!",
                    "rel_file": self.path,
                    "test_done": True,
                }
                yield log_entry

    def chart_save(self):
        os.chdir(dirname(self.chart_dir))
        try_count = 0
        wrong_naming = False
        if not (self.name.endswith('chart') or self.name.endswith('workflow')):
            log_entry = {
                "suite": suite_tag,
                "test": "{}:{}".format(self.name, self.version),
                "step": "Helm save",
                "log": "",
                "loglevel": "ERROR",
                "timestamp": get_timestamp(),
                "message": "Chart save failed: {} due to name error. Name of chart has to end with -chart or -workflow!".format(self.name),
                "rel_file": self.path,
                "test_done": True,
            }
            yield log_entry
        else:

            command = ["helm", "chart", "save", self.name, f"{HelmChart.default_registry}/{self.name}:{self.version}"]
            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60)
            while output.returncode != 0 and try_count < HelmChart.max_tries:
                print("Error save -> try: {}".format(try_count))
                output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=60)
                try_count += 1
            log = make_log(std_out=output.stdout, std_err=output.stderr)

            if output.returncode != 0 or "The Kubernetes package manager" in output.stdout:
                log_entry = {
                    "suite": suite_tag,
                    "test": "{}:{}".format(self.name, self.version),
                    "step": "Helm save",
                    "log": log,
                    "loglevel": "ERROR",
                    "timestamp": get_timestamp(),
                    "message": "save failed: {}".format(self.name),
                    "rel_file": self.path,
                    "test_done": True,
                }
                yield log_entry

            else:
                log_entry = {
                    "suite": suite_tag,
                    "test": "{}:{}".format(self.name, self.version),
                    "step": "Helm save",
                    "log": log,
                    "loglevel": "DEBUG",
                    "timestamp": get_timestamp(),
                    "message": "Chart saved successfully!",
                    "rel_file": self.path,
                    "test_done": True,
                }
                yield log_entry

    @staticmethod
    def check_repos(user, pwd):
        for repo in HelmChart.repos_needed:
            if repo.startswith('file://'):
                continue
            command = ["helm", "repo", "add", "--username", user, "--password", pwd, repo, HelmChart.default_registry + repo]
            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=30)
            log = make_log(std_out=output.stdout, std_err=output.stderr)

            if output.returncode != 0 and '401 Unauthorized' in output.stderr:
                print("Could not add repo: {}".format(repo))
                log_entry = {
                    "suite": suite_tag,
                    "test": "Add repos",
                    "step": repo,
                    "loglevel": "ERROR",
                    "timestamp": get_timestamp(),
                    "log": log,
                    "message": "Access denied! -> check credentials + repo access!",
                    "rel_file": "",
                }
                yield log_entry

            elif output.returncode != 0:
                log_entry = {
                    "suite": suite_tag,
                    "test": "Add repos",
                    "step": repo,
                    "loglevel": "ERROR",
                    "timestamp": get_timestamp(),
                    "log": log,
                    "message": "repo add failed: {}".format(repo),
                    "rel_file": "",
                }
                yield log_entry

            else:
                log_entry = {
                    "suite": suite_tag,
                    "test": "Add repos",
                    "step": repo,
                    "loglevel": "DEBUG",
                    "timestamp": get_timestamp(),
                    "log": "",
                    "message": "Repo has been added successfully!",
                    "rel_file": "",
                }
                yield log_entry
        log_entry = {
            "suite": suite_tag,
            "test": "Add repos",
            "loglevel": "DEBUG",
            "timestamp": get_timestamp(),
            "test_done": True
        }
        yield log_entry

    @staticmethod
    def quick_check():
        chartfiles = glob.glob(HelmChart.kaapana_dir+"/**/Chart.yaml", recursive=True)
        chartfiles = sorted(chartfiles, key=lambda p: (-p.count(os.path.sep), p))

        print("Found {} Charts".format(len(chartfiles)))

        charts_list = []
        for chartfile in chartfiles:
            if "templates_and_examples" in chartfile:
                continue

            chart_object = HelmChart(chartfile)

            if not chart_object.nested:
                for log in chart_object.log_list:
                    yield log
                charts_list.append(chart_object)

        print("")
        print("-> quick_check done. ")
        print("")
        yield charts_list


############################################################
######################   START   ###########################
############################################################

def init_helm_charts(kaapana_dir, chart_registry):
    HelmChart.kaapana_dir = kaapana_dir
    HelmChart.default_registry = chart_registry
    check_helm_installed()


if __name__ == '__main__':
    print("Please use the 'start_build.py' script to launch the build-process.")
    exit(1)
