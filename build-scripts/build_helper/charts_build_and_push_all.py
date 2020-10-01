#!/usr/bin/env python3
import sys
import glob
import os
import json
from subprocess import PIPE, run

from shutil import copyfile
from argparse import ArgumentParser
from time import time
from pathlib import Path

suite_tag = "Helm Charts"
build_ready_list = None


def get_timestamp():
    return str(int(time() * 1000))


def check_helm_installed():
    command = ["helm", "push", "--help"]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=10)

    if output.returncode != 0 or "The Kubernetes package manager" in output.stdout:
        print("Helm ist not installed correctly!")
        print("Make sure Helm > v3 and the 'push'-plugin is installed!")
        print("hint: helm plugin install https://github.com/chartmuseum/helm-push")
        exit(1)

    command = ["helm", "kubeval", "--help"]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=3)
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
    repos_needed = []
    docker_containers_used = {}
    max_tries = 3
    default_registry = None
    default_project = None
    kaapana_dir = None

    def __eq__(self, other):
        return "{}:{}".format(self.name, self.version) == "{}:{}".format(other.name, other.version)

    def __init__(self, chartfile):
        self.name = None
        self.repo = None
        self.version = None
        self.nested = False
        self.log_list = []
        self.chartfile = chartfile

        if not os.path.isfile(chartfile):
            print("ERROR: Chartfile not found.")
            exit(1)

        if os.path.dirname(os.path.dirname(chartfile)).split("/")[-1] == "charts":
            self.nested = True

        with open(chartfile) as f:
            read_file = f.readlines()
            read_file = [x.strip() for x in read_file]

            for line in read_file:
                if "name:" in line:
                    self.name = line.split(": ")[1].strip()
                elif "repo:" in line:
                    self.repo = line.split(": ")[1].strip()
                elif "version:" in line:
                    self.version = line.split(": ")[1].strip()

        if self.repo is None:
            self.repo = HelmChart.default_project

        if self.name is not None and self.version is not None and self.repo is not None:
            self.name = name
            self.repo = repo
            self.version = version
            self.path = chartfile
            self.chart_dir = os.path.dirname(chartfile)
            self.dev = False
            self.requirements_ready = False
            self.nested = nested
            self.requirements = []

            if "-vdev" in self.version:
                self.dev = True

            self.chart_id = "{}/{}:{}".format(self.repo, self.name, self.version)

            print("")
            print("Adding new chart:")
            print("name: {}".format(self.name))
            print("version: {}".format(self.version))
            print("repo: {}".format(self.repo))
            print("chart_id: {}".format(self.chart_id))
            print("dev: {}".format(self.dev))
            print("nested: {}".format(self.nested))
            print("file: {}".format(self.chartfile))
            print("")

            if self.repo not in HelmChart.repos_needed:
                HelmChart.repos_needed.append(self.repo)

            if not self.nested:
                for log_entry in self.check_requirements():
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
            print("repo: {}".format(self.repo if self.name is not None else ""))
            print("file: {}".format(self.chartfile if self.name is not None else ""))
            print("")
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("")

    def check_requirements(self):
        log_list = []
        for requirements_file in Path(self.chart_dir).rglob('requirements.yaml'):
            with open(str(requirements_file)) as f:
                requirements_file = f.readlines()
            requirements_file = [x.strip() for x in requirements_file]
            last_req_name = ""
            last_req_version = ""
            req_repo = ""

            req_names_count = 0
            req_version_count = 0
            req_repo_count = 0

            for line in requirements_file:
                if "name:" in line and "#" not in line:
                    req_names_count += 1
                    last_req_name = line.split(": ")[1].strip()
                if "version:" in line and "#" not in line:
                    req_version_count += 1
                    last_req_version = line.split(": ")[1].strip()
                if "repository:" in line and "#" not in line:
                    req_repo_count += 1
                    req_repo = line.split("/")[-1].strip()

                if req_repo != "" and last_req_name != "" and last_req_version != "":
                    req_id = "{}/{}:{}".format(req_repo,
                                               last_req_name, last_req_version)

                    if req_id not in self.requirements:
                        self.requirements.append(req_id)

                    last_req_name = ""
                    last_req_version = ""
                    req_repo = ""

            if not (req_names_count == req_repo_count == req_version_count):
                log_entry = {
                    "suite": suite_tag,
                    "test": "{}:{}".format(self.name, self.version),
                    "step": "Requirements",
                    "loglevel": "FATAL",
                    "timestamp": get_timestamp(),
                    "log": "",
                    "message": "Something went wrong with requirements extraction.",
                    "rel_file": self.chart_dir,
                }
                log_list.append(log_entry)
            else:
                log_entry = {
                    "suite": suite_tag,
                    "test": "{}:{}".format(self.name, self.version),
                    "step": "Requirements",
                    "loglevel": "DEBUG",
                    "timestamp": get_timestamp(),
                    "log": "",
                    "message": "Requirements extracted successfully.",
                    "rel_file": self.chart_dir,
                }
                log_list.append(log_entry)

        return log_list

    def check_container_use(self):
        glob_path = '{}/templates/*.yaml'.format(self.chart_dir)
        for yaml_file in glob.glob(glob_path, recursive=True):
            with open(yaml_file, "r") as yaml_content:
                for line in yaml_content:
                    line = line.rstrip()
                    if "dktk-jip-registry.dkfz.de" in line and "image" in line and "#" not in line:
                        docker_container = "dktk-jip-registry.dkfz.de" + \
                            line.split(
                                "dktk-jip-registry.dkfz.de")[1].replace(" ", "").replace(",", "").lower()
                        if docker_container not in HelmChart.docker_containers_used.keys():
                            HelmChart.docker_containers_used[docker_container] = yaml_file

    def dep_up(self, chart_dir=None, log_list=[]):
        if chart_dir is None:
            chart_dir = self.chart_dir
            log_list = []

        dep_charts = os.path.join(chart_dir, "charts")
        if os.path.isdir(dep_charts):
            for item in os.listdir(dep_charts):
                path = os.path.join(dep_charts, item)
                if os.path.isdir(path):
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
        if os.path.exists(requirements_lock):
            os.remove(requirements_lock)

    def lint_chart(self):
        os.chdir(self.chart_dir)
        command = ["helm", "lint"]
        output = run(command, stdout=PIPE, stderr=PIPE,
                     universal_newlines=True, timeout=5)
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
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=10)
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
        os.chdir(os.path.dirname(self.chart_dir))
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

    def push(self):
        os.chdir(os.path.dirname(self.chart_dir))
        try_count = 0

        command = ["helm", "push", self.name, self.repo]
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
                "step": "Helm push",
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

    @staticmethod
    def check_repos(user, pwd):
        for repo in HelmChart.repos_needed:
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
        global build_ready_list
        build_ready_list = []

        chartfiles = glob.glob(HelmChart.kaapana_dir+"/**/Chart.yaml", recursive=True)
        chartfiles = sorted(chartfiles, key=lambda p: (-p.count(os.path.sep), p))

        chartfiles_count = len(chartfiles)
        print("Found {} Charts".format(len(chartfiles)))

        charts_list = []
        for chartfile in chartfiles:
            if "node_modules" in chartfile:
                log_entry = {
                    "suite": suite_tag,
                    "test": chartfile.split("/")[-2],
                    "step": "NODE_MODULE Check",
                    "log": "",
                    "loglevel": "WARN",
                    "timestamp": get_timestamp(),
                    "message": "Found node_module chartfile.",
                    "rel_file": chartfile,
                    "test_done": True,
                }
                yield log_entry
                continue

            chart_object = HelmChart(chartfile)

            if not chart_object.nested:
                for log in chart_object.log_list:
                    yield log
                charts_list.append(chart_object)

        resolve_tries = 0

        while resolve_tries <= HelmChart.max_tries and len(charts_list) != 0:
            resolve_tries += 1

            to_do_charts = []
            for chart in charts_list:
                if len(chart.requirements) == 0:
                    build_ready_list.append(chart)
                else:
                    requirements_left = []
                    for requirement in chart.requirements:
                        found = False
                        for ready_chart in build_ready_list:
                            if requirement == ready_chart.chart_id:
                                found = True
                        if not found:
                            requirements_left.append(requirement)

                    chart.requirements = requirements_left

                    if len(requirements_left) > 0:
                        to_do_charts.append(chart)
                    else:
                        log_entry = {
                            "suite": suite_tag,
                            "test": chart.name,
                            "step": "Check Dependencies",
                            "log": "",
                            "loglevel": "DEBUG",
                            "timestamp": get_timestamp(),
                            "message": "All dependencies ok",
                            "rel_file": "",
                        }
                        build_ready_list.append(chart)
                        yield log_entry

            charts_list = to_do_charts

        if resolve_tries > HelmChart.max_tries:
            for chart in reversed(charts_list):
                miss_deps = []
                for req in chart.requirements:
                    miss_deps.append(req)

                log_entry = {
                    "suite": suite_tag,
                    "test": chart.name,
                    "step": "Check Dependencies",
                    "log": {"Missing dependency": miss_deps},
                    "loglevel": "ERROR",
                    "timestamp": get_timestamp(),
                    "message": "Could not resolve all dependencies",
                    "rel_file": "",
                }
                yield log_entry
                build_ready_list.append(chart)

        else:
            log_entry = {
                "suite": suite_tag,
                "test": chart.name,
                "step": "Check Dependencies",
                "log": "",
                "loglevel": "DEBUG",
                "timestamp": get_timestamp(),
                "message": "Successful",
                "rel_file": "",
            }
            yield log_entry

        yield build_ready_list


############################################################
######################   START   ###########################
############################################################

def init_helm_charts(kaapana_dir, chart_registry, default_project):
    HelmChart.kaapana_dir = kaapana_dir
    HelmChart.default_registry = chart_registry
    HelmChart.default_project = default_project
    check_helm_installed()


if __name__ == '__main__':
    print("Please use the 'start_build.py' script to launch the build-process.")
    exit(1)
