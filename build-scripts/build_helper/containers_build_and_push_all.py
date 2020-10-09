#!/usr/bin/env python3
import sys
import glob
import os
import json
from subprocess import PIPE, run
from time import time
from shutil import which

suite_tag = "Docker Container"


def get_timestamp():
    return str(int(time() * 1000))


def generate_image_version_list(container_list):
    base_images_dict = {}

    for container in container_list:
        for base_image in container.base_images:
            if base_image not in base_images_dict.keys():
                base_images_dict[base_image] = []

            base_images_dict[base_image].append(container.tag.replace(container.docker_registry, "")[1:])

    sorted_tags = sorted(base_images_dict, key=lambda k: len(base_images_dict[k]), reverse=True)

    result_list = []
    for sorted_tag in sorted_tags:
        result_list.append({
            "BASE_IMAGE": sorted_tag,
            "TAGS": base_images_dict[sorted_tag]
        })
    file_path = os.path.join(kaapana_dir, "CI", "used_base_images.json")
    with open(file_path, 'w+', encoding='utf-8') as f:
        json.dump(result_list, f, ensure_ascii=False, indent=4, sort_keys=True)

    print("############################# generate_image_version_list -> done.")


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

class DockerContainer:
    used_tags_list = []

    def __eq__(self, other):
        return self.tag == other.tag

    def __str__(self):
        return "tag: {} path: {} base_images: {}".format(self.tag, self.path, self.base_images)

    def get_dict(self):
        repr_obj = {
            "tag": self.tag,
            "path": self.path,
            "base_images": self.base_images,
        }
        return repr_obj

    def __init__(self, dockerfile):
        self.maintainers = {}
        self.docker_registry = None
        self.project_name = None
        self.image_name = None
        self.image_version = None
        self.tag = None
        self.path = dockerfile
        self.ci_ignore = False
        self.error = False
        self.pending = False
        self.dev = False
        self.airflow_component = False
        self.container_dir = os.path.dirname(dockerfile)
        self.log_list = []
        self.base_images = []

        if not os.path.isfile(dockerfile):
            print("ERROR: Dockerfile not found.")
            exit(1)

        with open(dockerfile, 'rt') as f:
            lines = f.readlines()
            for line in lines:
                if line.__contains__('LABEL REGISTRY='):
                    self.docker_registry = line.split("=")[1].rstrip().strip().replace("\"", "")
                elif line.__contains__('LABEL REGISTRY_PROJECT='):
                    self.project_name = line.split("=")[1].rstrip().strip().replace("\"", "")
                elif line.__contains__('LABEL IMAGE='):
                    self.image_name = line.split("=")[1].rstrip().strip().replace("\"", "")
                elif line.__contains__('LABEL VERSION='):
                    self.image_version = line.split("=")[1].rstrip().strip().replace("\"", "")
                elif line.__contains__('FROM') and not line.__contains__('#ignore'):
                    self.base_images.append(line.split("FROM ")[1].split(" ")[0].rstrip().strip().replace("\"", ""))
                elif line.__contains__('LABEL CI_IGNORE='):
                    self.ci_ignore = True if line.split("=")[1].rstrip().strip().replace("\"", "").lower() == "true" else False

        if self.docker_registry == None:
            self.docker_registry = default_registry
        if self.project_name is None and default_project is not None and self.docker_registry.lower() != "local":
            self.project_name = default_project

        if self.image_version != None and self.image_name != None and self.image_version != "" and self.image_name != "":
            if self.project_name is not None:
                self.tag = self.docker_registry+"/"+self.project_name + "/"+self.image_name+":"+self.image_version
            else:
                self.tag = self.docker_registry+"/"+self.image_name+":"+self.image_version
                
            self.check_pending()

            log_entry = {
                "suite": suite_tag,
                "test": self.tag.replace(self.docker_registry, "")[1:],
                "step": "Docker-Tag Extraction",
                "log": "",
                "loglevel": "DEBUG",
                "timestamp": get_timestamp(),
                "message": "Docker-tag extraction successful!",
                "rel_file": self.path,
                "container": self,
            }
            self.log_list.append(log_entry)

            if "-vdev" in self.image_version:
                self.dev = True

            self.check_if_airflow_component()

        else:
            log_entry = {
                "suite": suite_tag,
                "test": dockerfile,
                "step": "Docker-Tag Extraction",
                "log": "",
                "loglevel": "WARN",
                "timestamp": get_timestamp(),
                "message": "Could not extract container info",
                "rel_file": dockerfile,
            }
            self.log_list.append(log_entry)
            self.error = True

    def check_pending(self):
        if self.tag in DockerContainer.used_tags_list:
            log_entry = {
                "suite": suite_tag,
                "test": self.tag.replace(self.docker_registry, "")[1:],
                "step": "Docker-Tag Extraction",
                "log": "",
                "loglevel": "ERROR",
                "timestamp": get_timestamp(),
                "message": "This tag was already used by another Dockerfile!",
                "rel_file": self.path,
                "container": self,
            }
            self.log_list.append(log_entry)
            self.pending = False
            self.error = True
        else:
            for base_image in self.base_images:
                # if base_image not in DockerContainer.used_tags_list:
                if default_registry in base_image and base_image not in DockerContainer.used_tags_list:
                    self.pending = True
                else:
                    DockerContainer.used_tags_list.append(self.tag)
                    self.pending = False

        return self.pending

    def check_if_airflow_component(self):
        if "." in os.path.basename(self.path):
            airflow_components_path = "{}/airflow-components".format(os.path.dirname(os.path.dirname(os.path.dirname(self.path))))
            sub_dirs = glob.glob("{}/*/".format(airflow_components_path))
            sub_dirs = [sub_dir.split("/")[-2] for sub_dir in sub_dirs]

            if "dags" not in sub_dirs and "plugins" not in sub_dirs:
                log_entry = {
                    "suite": suite_tag,
                    "test": self.tag.replace(self.docker_registry, "")[1:],
                    "step": "Airflow Component",
                    "log": "",
                    "loglevel": "ERROR",
                    "timestamp": get_timestamp(),
                    "message": "Dockerfile not valid: filename with '.' and not a dag",
                    "rel_file": self.path,
                    "container": self,
                }
                self.log_list.append(log_entry)
                self.airflow_component = False
                self.error = True
            else:
                log_entry = {
                    "suite": suite_tag,
                    "test": self.tag.replace(self.docker_registry, "")[1:],
                    "step": "Airflow Component",
                    "log": "",
                    "loglevel": "DEBUG",
                    "timestamp": get_timestamp(),
                    "message": "Dockerfile is a valid airflow dag container.",
                    "rel_file": self.path,
                    "container": self,
                }
                self.log_list.append(log_entry)
                self.container_dir = airflow_components_path
                self.airflow_component = True
        else:
            log_entry = {
                "suite": suite_tag,
                "test": self.tag.replace(self.docker_registry, "")[1:],
                "step": "Airflow Component",
                "log": "",
                "loglevel": "DEBUG",
                "timestamp": get_timestamp(),
                "message": "Dockerfile is no airflow component.",
                "rel_file": self.path,
                "container": self,
            }
            self.log_list.append(log_entry)

    def check_prebuild(self):
        pre_build_script = os.path.dirname(self.path)+"/pre_build.sh"
        if os.path.isfile(pre_build_script):
            command = [pre_build_script]
            output = run(command, stdout=PIPE, stderr=PIPE,universal_newlines=True, timeout=3600)
            log = make_log(std_out=output.stdout, std_err=output.stderr)

            if output.returncode == 0:
                log_entry = {
                    "suite": suite_tag,
                    "test": self.tag.replace(self.docker_registry, "")[1:],
                    "step": "check_prebuild",
                    "log": log,
                    "loglevel": "DEBUG",
                    "timestamp": get_timestamp(),
                    "message": "pre_build.sh successful.",
                    "rel_file": pre_build_script,
                    "container": self,
                }
                yield log_entry

            else:
                log_entry = {
                    "suite": suite_tag,
                    "test": self.tag.replace(self.docker_registry, "")[1:],
                    "step": "check_prebuild",
                    "log": log,
                    "loglevel": "ERROR",
                    "timestamp": get_timestamp(),
                    "message": "pre_build.sh execution error.",
                    "rel_file": pre_build_script,
                    "container": self,
                }
                self.error = True
                yield log_entry
        else:
            log_entry = {
                "suite": suite_tag,
                "test": self.tag.replace(self.docker_registry, "")[1:],
                "step": "check_prebuild",
                "log": "",
                "loglevel": "DEBUG",
                "timestamp": get_timestamp(),
                "message": "No pre_build.sh found.",
                "rel_file": pre_build_script,
                "container": self,
            }
            yield log_entry

    def build(self):
        print("############################ Build Container: {}".format(self.tag))
        os.chdir(self.container_dir)
        if http_proxy is not None:
            command = ["docker", "build", "--build-arg", "http_proxy={}".format(http_proxy), "--build-arg", "https_proxy={}".format(http_proxy), "-t", self.tag, "-f", self.path, "."]
        else:
            command = ["docker", "build", "-t", self.tag, "-f", self.path, "."]

        output = run(command, stdout=PIPE, stderr=PIPE,universal_newlines=True, timeout=6000)
        log = make_log(std_out=output.stdout, std_err=output.stderr)

        if output.returncode != 0:
            log_entry = {
                "suite": suite_tag,
                "test": self.tag.replace(self.docker_registry, "")[1:],
                "step": "Docker build",
                "log": log,
                "loglevel": "ERROR",
                "timestamp": get_timestamp(),
                "message": "Build failed!",
                "rel_file": self.path,
                "container": self,
                "test_done": True,
            }
            self.error = True
            yield log_entry

        print("############################ Build -> success")
        log_entry = {
            "suite": suite_tag,
            "test": self.tag.replace(self.docker_registry, "")[1:],
            "step": "Docker build",
            "log": "",
            "loglevel": "DEBUG",
            "timestamp": get_timestamp(),
            "message": "Build successful",
            "rel_file": self.path,
            "container": self,
        }
        yield log_entry

    def push(self, retry=True):
        max_retires = 2
        retries = 0

        print()
        print("############################ Push Container: {}".format(self.tag))
        command = ["docker", "push", self.tag]

        while retries < max_retires:
            retries += 1
            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=3600)
            if output.returncode == 0 or "configured as immutable" in output.stderr:
                break

        log = make_log(std_out=output.stdout, std_err=output.stderr)

        if output.returncode == 0 and "Pushed" in output.stdout:
            print("############################ Push -> success")
            print()
            log_entry = {
                "suite": suite_tag,
                "test": self.tag.replace(self.docker_registry, "")[1:],
                "step": "Docker push",
                "log": "",
                "loglevel": "DEBUG",
                "timestamp": get_timestamp(),
                "message": "Push successful",
                "rel_file": self.path,
                "container": self,
                "test_done": True,
            }
            yield log_entry

        elif output.returncode == 0:
            print(
                "############################ Push successful -> but nothing was changed")
            log_entry = {
                "suite": suite_tag,
                "test": self.tag.replace(self.docker_registry, "")[1:],
                "step": "Docker push",
                "log": "",
                "loglevel": "DEBUG",
                "timestamp": get_timestamp(),
                "message": "Push successful, but nothing was changed!",
                "rel_file": self.path,
                "container": self,
                "test_done": True,
            }
            yield log_entry

        elif output.returncode != 0 and "configured as immutable" in output.stderr:
            print(
                "############################ Push -> immutable -> no -vdev version -> ok")
            if "-vdev" not in self.tag:
                log_entry = {
                    "suite": suite_tag,
                    "test": self.tag.replace(self.docker_registry, "")[1:],
                    "step": "Docker push",
                    "log": "",
                    "loglevel": "DEBUG",
                    "timestamp": get_timestamp(),
                    "message": "Push skipped -> image version immutable and no -vdev version!",
                    "rel_file": self.path,
                    "container": self,
                    "test_done": True,
                }
                yield log_entry

            else:
                log_entry = {
                    "suite": suite_tag,
                    "test": self.tag.replace(self.docker_registry, "")[1:],
                    "step": "Docker push",
                    "log": log,
                    "loglevel": "ERROR",
                    "timestamp": get_timestamp(),
                    "message": "Push failed! -> image version immutable and -vdev version!",
                    "rel_file": self.path,
                    "container": self,
                    "test_done": True,
                }
                self.error = True
                yield log_entry

        elif output.returncode != 0 and "read only mode" in output.stderr and retry:
            print("############################ Push -> read only mode -> RETRY!")
            log_entry = {
                "suite": suite_tag,
                "test": self.tag.replace(self.docker_registry, "")[1:],
                "step": "Docker push",
                "log": "",
                "loglevel": "WARN",
                "timestamp": get_timestamp(),
                "message": "Push read only mode!",
                "rel_file": self.path,
                "container": "",
            }
            yield log_entry
            self.push(retry=False)

        else:
            print("############################ Push -> ERROR!")
            log_entry = {
                "suite": suite_tag,
                "test": self.tag.replace(self.docker_registry, "")[1:],
                "step": "Docker push",
                "log": log,
                "loglevel": "ERROR",
                "timestamp": get_timestamp(),
                "message": "Push failed!",
                "rel_file": self.path,
                "container": self,
                "test_done": True,
            }
            self.error = True
            yield log_entry


def quick_check():
    DockerContainer.used_tags_list = []
    dockerfiles_small = glob.glob(kaapana_dir+"/**/dockerfile*", recursive=True)
    for wrong in dockerfiles_small:
        if "node_modules" in wrong:
            continue
        log_entry = {
            "suite": suite_tag,
            "test": "Dockerfile checks",
            "step": wrong,
            "log": "",
            "loglevel": "ERROR",
            "timestamp": get_timestamp(),
            "message": "Dockerfile not valid: filename must be capitalized",
            "rel_file": wrong,
        }
        yield log_entry

    dockerfiles = glob.glob(kaapana_dir+"/**/Dockerfile*", recursive=True)
    print("Found {} Dockerfiles".format(len(dockerfiles)))

    docker_containers_list = []
    docker_containers_pending_list = []
    for dockerfile in dockerfiles:
        docker_container = DockerContainer(dockerfile)
        for log_entry in docker_container.log_list:
            yield log_entry

        if docker_container.error:
            continue

        else:
            log_entry = {
                "suite": suite_tag,
                "test": docker_container.tag.replace(docker_container.docker_registry, "")[1:],
                "step": "Docker-Tag Check",
                "log": "",
                "loglevel": "DEBUG",
                "timestamp": get_timestamp(),
                "message": "Docker tag ok!",
                "rel_file": docker_container.path,
                "container": docker_container,
            }
            yield log_entry

            if docker_container.pending:
                docker_containers_pending_list.append(docker_container)
            else:
                docker_containers_list.append(docker_container)

    max_tries = 5
    try_count = 0

    while try_count <= max_tries:
        try_count += 1
        pending_copy = docker_containers_pending_list.copy()
        for pending_container in pending_copy:
            if not pending_container.check_pending():
                docker_containers_list.append(docker_container)
                docker_container.used_tags_list.append(docker_container.tag)
                docker_containers_pending_list.remove(pending_container)

    for not_resolved in docker_containers_pending_list:
        log_entry = {
            "suite": suite_tag,
            "test": not_resolved.tag.replace(not_resolved.docker_registry, "")[1:],
            "step": "Base-Image Check",
            "log": "",
            "loglevel": "WARN",
            "timestamp": get_timestamp(),
            "message": "Could not resolve base image: {}".format(not_resolved.base_images),
            "rel_file": not_resolved.path,
            "container": "",
        }

        if not_resolved.tag not in DockerContainer.used_tags_list:
            docker_containers_list.append(not_resolved)
            docker_container.used_tags_list.append(not_resolved.tag)
        
        yield log_entry

    yield docker_containers_list


def start_container_build(config):
    global kaapana_dir, http_proxy, default_registry, default_project
    kaapana_dir, http_proxy, default_registry, default_project = config

    if which("docker") is None:
        print("Docker was not found!")
        print("Please install Docker on your system.")
        exit(1)

    logs = []
    for log in quick_check():
        if type(log) != dict:
            docker_containers_list = log
        else:
            logs.append(log)

    print()
    print("Process {} containers...".format(len(docker_containers_list)))
    print()

    return [docker_containers_list,logs]


if __name__ == '__main__':
    print("Please use the 'start_build.py' script to launch the build-process.")
    exit(1)
