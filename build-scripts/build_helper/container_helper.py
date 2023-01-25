#!/usr/bin/env python3
from glob import glob
import os
from subprocess import PIPE, run
from time import time
from shutil import which
from build_helper.build_utils import BuildUtils

suite_tag = "Container"
max_retries = 5


def container_registry_login(username, password):
    BuildUtils.logger.info(f"-> Container registry-logout: {BuildUtils.default_registry}")
    command = [Container.container_engine, "logout", BuildUtils.default_registry]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=10)

    if output.returncode != 0:
        BuildUtils.logger.info(f"Docker couldn't logout from registry: {BuildUtils.default_registry} -> not logged in!")

    BuildUtils.logger.info(f"-> Container registry-login: {BuildUtils.default_registry}")
    command = [Container.container_engine, "login", BuildUtils.default_registry, "--username", username, "--password", password]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=10)

    if output.returncode != 0:
        BuildUtils.logger.error("Something went wrong!")
        BuildUtils.logger.error(f"Couldn't login into registry {BuildUtils.default_registry}")
        BuildUtils.logger.error(f"Message: {output.stdout}")
        BuildUtils.logger.error(f"Error:   {output.stderr}")
        exit(1)

def pull_container_image(image_tag):
    command = [Container.container_engine, "pull", image_tag]
    print(f"Pulling container image: {image_tag}")
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=6000, env=dict(os.environ, DOCKER_BUILDKIT=f"{BuildUtils.enable_build_kit}"))

    if output.returncode == 0:
        print(f"sucess!")

    else:
        print(f"Something went wrong...")

class BaseImage:
    registry = None
    project = None
    name = None
    version = None
    tag = None
    local_image = None

    def __eq__(self, other):
        return self.tag == other.tag

    def get_dict(self):
        base_img_dict = {
            "name": self.name,
            "version": self.version,
            "tag": self.tag
        }
        return base_img_dict

    def __init__(self, tag):
        if ":" not in tag:
            BuildUtils.logger.error(f"{tag}: Could not extract base-image version!")
            BuildUtils.generate_issue(
                component=suite_tag,
                name=f"{tag}",
                msg="Could not extract base-image version!",
                level="ERROR"
            )

        self.local_image = False
        if "local-only" in tag:
            self.registry = "local-only"
            self.project = ""
            self.name = tag.split("/")[1].split(":")[0]
            self.local_image = True
        elif tag.count("/") == 0:
            self.registry = "Dockerhub"
            self.project = ""
            self.name = tag.split(":")[0]
        elif tag.count("/") == 1:
            self.registry = "Dockerhub"
            self.project = tag.split("/")[0]
            self.name = tag.split("/")[1].split(":")[0]
        elif tag.count("/") == 2:
            self.registry = tag.split("/")[0]
            self.project = tag.split("/")[1]
            self.name = tag.split("/")[2].split(":")[0]
        elif tag.count("/") == 3:
            self.registry = tag.split("/")[0]
            self.project = f"{tag.split('/')[1]}/{tag.split('/')[2]}"
            self.name = tag.split("/")[3].split(":")[0]
        else:
            BuildUtils.logger.error("Could not extract base-image!")
            exit(1)

        self.version = tag.split(":")[1]
        self.tag = tag
        self.present = None


class Container:
    container_engine = None
    external_sources = None
    container_object_list = None
    container_build_status = None
    container_push_status = None
    local_image = None

    def __eq__(self, other):
        if isinstance(self, str):
            self_tag = self
        else:
            self_tag = self.tag

        if isinstance(other, str):
            other_tag = other
        else:
            other_tag = other.tag

        return self_tag == other_tag

    def __str__(self):
        return f"tag: {self.tag}"

    def get_dict(self):
        repr_obj = {
            "tag": self.tag,
            "path": self.path,
            "base_images": [],
        }
        for base_image in self.base_images:
            repr_obj["base_images"].append(base_image.get_dict())

        return repr_obj

    def __init__(self, dockerfile=None):
        if dockerfile == None:
            return

        self.image_name = None
        self.image_version = None
        self.repo_version = None
        self.tag = None
        self.path = dockerfile
        self.ci_ignore = False
        self.pending = False
        self.airflow_component = False
        self.container_dir = os.path.dirname(dockerfile)
        self.log_list = []
        self.base_images = []
        self.missing_base_images = None
        self.registry = None
        self.already_built = False
        self.container_build_status = "None"
        self.container_push_status = "None"
        self.local_image = False
        self.build_tag = None
        self.operator_containers = None

        if not os.path.isfile(dockerfile):
            BuildUtils.logger.error(f"Dockerfile {dockerfile} not found.")
            if BuildUtils.exit_on_error:
                exit(1)

        with open(dockerfile, 'rt') as f:
            lines = f.readlines()
            for line in lines:
                if "#" in line:
                    line = line[:line.index("#")]
                if line.strip() == "":
                    continue

                if line.__contains__('LABEL REGISTRY='):
                    self.registry = line.split("#")[0].split("=")[1].rstrip().strip().replace("\"", "")
                elif line.__contains__('LABEL IMAGE='):
                    self.image_name = line.split("#")[0].split("=")[1].rstrip().strip().replace("\"", "")
                elif line.__contains__('LABEL VERSION='):
                    self.repo_version = line.split("#")[0].split("=")[1].rstrip().strip().replace("\"", "")
                elif line.startswith('FROM') and not line.__contains__('#ignore'):
                    base_img_tag = line.split("#")[0].split("FROM ")[1].split(" ")[0].rstrip().strip().replace("\"", "")
                    base_img_obj = BaseImage(tag=base_img_tag)
                    if base_img_obj not in self.base_images:
                        self.base_images.append(base_img_obj)
                        if base_img_obj not in BuildUtils.base_images_used:
                            BuildUtils.base_images_used.append(base_img_obj)
                elif line.__contains__('LABEL CI_IGNORE='):
                    self.ci_ignore = True if line.split("#")[0].split("=")[1].rstrip().lower().replace("\"", "").replace("'", "") == "true" else False

        if self.repo_version == None and self.repo_version == "" or self.image_name == None or self.image_name == "":
            BuildUtils.logger.debug(f"{self.container_dir}: could not extract container infos!")
            BuildUtils.generate_issue(
                component=suite_tag,
                name=f"{self.container_dir}",
                msg="could not extract container infos!",
                level="ERROR",
            )
            return

        else:

            self.registry = self.registry if self.registry != None else BuildUtils.default_registry
            if "local-only" in self.registry:
                self.local_image = True
                self.repo_version = "latest"

            else:
                build_version, build_branch, last_commit, last_commit_timestamp = BuildUtils.get_repo_info(self.container_dir)
                self.repo_version = build_version

            self.tag = self.registry+"/"+self.image_name+":"+self.repo_version

        self.check_if_dag()

    def check_prebuild(self):
        BuildUtils.logger.debug(f"{self.build_tag}: check_prebuild")
        pre_build_script = os.path.dirname(self.path)+"/pre_build.sh"
        if os.path.isfile(pre_build_script):
            command = [pre_build_script]
            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=3600, cwd=self.container_dir)

            if output.returncode == 0:
                BuildUtils.logger.debug(f"{self.build_tag}: pre-build ok.")

            else:
                BuildUtils.logger.error(f"{self.build_tag}: pre-build failed!")
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name=f"{self.build_tag}",
                    msg="pre-build failed!",
                    level="ERROR",
                    output=output,
                    path=pre_build_script
                )

        else:
            BuildUtils.logger.debug(f"{self.build_tag}: no pre-build script!")

    def build(self):
        issue = None
        if Container.enable_build:
            BuildUtils.logger.debug(f"{self.build_tag}: start building ...")

            if self.container_push_status == "pushed":
                BuildUtils.logger.debug(f"{self.build_tag}: already build -> skip")
                return issue

            if self.ci_ignore:
                BuildUtils.logger.warning(f"{self.build_tag}: {self.ci_ignore=} -> skip")
                issue = {
                    "component": suite_tag,
                    "name": f"{self.build_tag}",
                    "msg": f"Container build skipped: {self.ci_ignore=} !",
                    "level": "WARING",
                    "path": self.container_dir
                }
                return issue

            startTime = time()
            if BuildUtils.http_proxy is not None:
                command = [Container.container_engine, "build", "--build-arg", f"http_proxy={BuildUtils.http_proxy}",
                           "--build-arg", f"https_proxy={BuildUtils.http_proxy}", "-t", self.build_tag, "-f", self.path, "."]
            else:
                command = [Container.container_engine, "build", "-t", self.build_tag, "-f", self.path, "."]

            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=6000, cwd=self.container_dir, env=dict(os.environ, DOCKER_BUILDKIT=f"{BuildUtils.enable_build_kit}"))

            if output.returncode == 0:
                if "---> Running in" in output.stdout:
                    self.container_build_status = "built"
                    BuildUtils.logger.debug(f"{self.build_tag}: Build sucessful.")
                else:
                    self.container_build_status = "nothing_changed"
                    BuildUtils.logger.debug(f"{self.build_tag}: Build sucessful - no changes.")

                hours, rem = divmod(time()-startTime, 3600)
                minutes, seconds = divmod(rem, 60)
                BuildUtils.logger.debug("{}: Build-time: {:0>2}:{:0>2}:{:05.2f}".format(self.build_tag, int(hours), int(minutes), seconds))
                return issue

            else:
                self.container_build_status = "failed"
                BuildUtils.logger.error(f"{self.build_tag}: Build failed!")
                issue = {
                    "component": suite_tag,
                    "name": f"{self.build_tag}",
                    "msg": "container build failed!",
                    "level": "ERROR",
                    "output": output,
                    "path": self.container_dir
                }
                return issue
        else:
            BuildUtils.logger.debug(f"{self.build_tag}: build disabled")
            self.container_build_status = "disabled"
            return issue

    def push(self, retry=True):
        issue = None
        BuildUtils.logger.debug(f"{self.build_tag}: in push()")
        if self.ci_ignore:
            BuildUtils.logger.warning(f"{self.build_tag}: {self.ci_ignore=} -> skip")
            issue = {
                "component": suite_tag,
                "name": f"{self.build_tag}",
                "msg": f"Container push skipped: {self.ci_ignore=} !",
                "level": "WARING",
                "path": self.container_dir
            }
            return issue

        if BuildUtils.push_to_microk8s is True:
            if self.build_tag.startswith('local-only'):
                BuildUtils.logger.info(f"Skipping: Pushing {self.build_tag} to microk8s, due to local-only")
                return issue
            BuildUtils.logger.debug(f"{self.build_tag}: push_to_microk8s")

            BuildUtils.logger.info(f"Pushing {self.build_tag} to microk8s")
            parking_file = "parking.tar"
            command = [Container.container_engine, "save", self.build_tag, "-o", parking_file]
            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=9000)
            if output.returncode != 0:
                BuildUtils.logger.error(f"Docker save failed {output.stderr}!")
                issue = {
                    "component": "Microk8s push",
                    "name": "docker save",
                    "msg": f"Docker save failed {output.stderr}!",
                    "level": "ERROR"
                }
                return issue

            command = ["microk8s", "ctr", "image", "import", parking_file]
            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=9000)
            if os.path.exists(parking_file):
                os.remove(parking_file)
            if output.returncode != 0:
                BuildUtils.logger.error(f"Microk8s image push failed {output.stderr}!")
                issue = {
                    "component": "Microk8s image push",
                    "name": "Microk8s image push",
                    "msg": f"Microk8s image push failed {output.stderr}!",
                    "level": "ERROR"
                }
                return issue

            BuildUtils.logger.debug(f"Sucessfully pushed {self.build_tag} to microk8s")

        if Container.enable_push:
            BuildUtils.logger.debug(f"{self.build_tag}: push enabled")

            if self.container_build_status == "nothing_changed":
                if BuildUtils.skip_push_no_changes:
                    BuildUtils.logger.info(f"{self.build_tag}: Image did not change -> skipping ...")
                    return
                else:
                    self.container_build_status = "built"

            if self.container_push_status == "pushed":
                BuildUtils.logger.info(f"{self.build_tag}: Already pushed -> skip")
                return

            elif self.container_build_status != "built":
                BuildUtils.logger.warning("{self.build_tag}: Skipping push since image has not been built successfully!")
                BuildUtils.logger.warning(f"{self.build_tag}: container_build_status: {self.container_build_status}")
                issue = {
                    "component": suite_tag,
                    "name": f"{self.build_tag}",
                    "msg": f"Push skipped -> image has not been built successfully! container_build_status: {self.container_build_status}",
                    "level": "WARNING",
                    "path": self.container_dir
                }
                return issue

            elif self.local_image:
                BuildUtils.logger.debug(f"{self.build_tag}: Skipping push: local image! ")
                return

            BuildUtils.logger.debug(f"{self.build_tag}: start pushing! ")
            retries = 0
            command = [Container.container_engine, "push", self.build_tag]
            while retries < max_retries:
                retries += 1
                output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=9000)
                if output.returncode == 0 or "configured as immutable" in output.stderr:
                    break

            if output.returncode == 0:
                self.container_push_status = "pushed"

                if "Pushed" in output.stdout or "podman" in Container.container_engine:
                    BuildUtils.logger.debug(f"{self.build_tag}: pushed -> success")
                else:
                    BuildUtils.logger.debug(f"{self.build_tag}: pushed -> success but nothing was changed!")

                return issue

            else:
                self.container_push_status = "not_pushed"

                if "configured as immutable" in output.stderr:
                    BuildUtils.logger.warning(f"{self.build_tag}: not pushed -> immutable!")
                    issue = {
                        "component": suite_tag,
                        "name": f"{self.build_tag}",
                        "msg": f"Container not pushed -> immutable!",
                        "level": "WARNING",
                        "path": self.container_dir
                    }

                elif "read only mode" in output.stderr and retry:
                    BuildUtils.logger.warning(f"{self.build_tag}: not pushed -> read only mode!")
                    issue = {
                        "component": suite_tag,
                        "name": f"{self.build_tag}",
                        "msg": f"Container not pushed -> read only mode!",
                        "level": "WARNING",
                        "path": self.container_dir
                    }

                elif "denied" in output.stderr and retry:
                    BuildUtils.logger.error(f"{self.build_tag}: not pushed -> access denied!")
                    issue = {
                        "component": suite_tag,
                        "name": f"{self.build_tag}",
                        "msg": "container not pushed -> access denied!",
                        "level": "ERROR",
                        "output": output,
                        "path": self.container_dir
                    }
                else:
                    BuildUtils.logger.error(f"{self.build_tag}: not pushed -> unknown reason!")
                    issue = {
                        "component": suite_tag,
                        "name": f"{self.build_tag}",
                        "msg": "container not pushed -> unknown reason!",
                        "level": "ERROR",
                        "output": output,
                        "path": self.container_dir
                    }

                return issue

        else:
            BuildUtils.logger.info(f"{self.build_tag}: push disabled")
            self.container_push_status = "disabled"
            return issue

    def check_if_dag(self):
        self.operator_containers = []
        python_files = glob(self.container_dir+"/**/*.py", recursive=True)
        for python_file in python_files:
            if "operator" not in python_file.lower():
                continue

            with open(python_file, "r") as python_content:
                for line in python_content:
                    if "image=" in line and "{default_registry}" in line:
                        line = line.rstrip('\n').split("\"")[1].replace(" ", "")
                        line = line.replace("{kaapana_build_version}", self.repo_version)
                        container_id = line.replace("{default_registry}", BuildUtils.default_registry)
                        self.operator_containers.append(container_id)

    @staticmethod
    def init_containers(container_engine, enable_build=True, enable_push=True):
        Container.container_engine = container_engine
        Container.enable_build = enable_build
        Container.enable_push = enable_push

        BuildUtils.logger.debug("")
        BuildUtils.logger.debug(" -> Container Init")
        BuildUtils.logger.debug(f"Container engine: {Container.container_engine}")
        if which(Container.container_engine) is None:
            BuildUtils.logger.error(f"{Container.container_engine} was not found!")
            BuildUtils.logger.error("Please install {Container.container_engine} on your system.")
            if BuildUtils.exit_on_error:
                exit(1)

    @staticmethod
    def collect_containers():
        BuildUtils.logger.debug("")
        BuildUtils.logger.debug(" collect_containers")
        Container.container_object_list = []
        Container.used_tags_list = []

        dockerfiles_found = glob(BuildUtils.kaapana_dir+"/**/Dockerfile*", recursive=True)
        BuildUtils.logger.info("")
        BuildUtils.logger.info(f"-> Found {len(dockerfiles_found)} Dockerfiles @Kaapana")

        if BuildUtils.external_source_dirs != None and len(BuildUtils.external_source_dirs) > 0:
            for external_source in BuildUtils.external_source_dirs:
                BuildUtils.logger.info("")
                BuildUtils.logger.info(f"-> adding external sources: {external_source}")
                dockerfiles_found.extend(glob(external_source+"/**/Dockerfile*", recursive=True))
                BuildUtils.logger.info(f"Found {len(dockerfiles_found)} Dockerfiles")
                BuildUtils.logger.info("")

        if len(dockerfiles_found) != len(set(dockerfiles_found)):
            BuildUtils.logger.warning("-> Duplicate Dockerfiles found!")

        dockerfiles_found = sorted(set(dockerfiles_found))

        for dockerfile in dockerfiles_found:
            container = Container(dockerfile)
            Container.container_object_list.append(container)

        Container.container_object_list = Container.check_base_containers(Container.container_object_list)
        return Container.container_object_list

    @staticmethod
    def check_base_containers(container_object_list):
        BuildUtils.logger.debug("")
        BuildUtils.logger.debug(" check_base_containers")
        BuildUtils.logger.debug("")
        for container in container_object_list:
            print(container)
        for container in container_object_list:
            container.missing_base_images = []
            for base_image in container.base_images:
                if base_image.local_image and base_image.tag not in Container.container_object_list:
                    container.missing_base_images.append(base_image)
                    BuildUtils.logger.error("")
                    BuildUtils.logger.error(f"-> {container.tag} - base_image missing: {base_image.tag}")
                    BuildUtils.logger.error("")
                    if BuildUtils.exit_on_error:
                        exit(1)

        return container_object_list


if __name__ == '__main__':
    print("Please use the 'start_build.py' script to launch the build-process.")
    exit(1)
