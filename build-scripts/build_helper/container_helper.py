#!/usr/bin/env python3
from glob import glob
import os
from subprocess import PIPE, run
from time import time, sleep
from shutil import which
from build_helper.build_utils import BuildUtils

suite_tag = "Container"
def container_registry_login(username, password):
    BuildUtils.logger.info(f"-> Container registry-logout: {BuildUtils.default_registry}")
    command = [Container.container_engine, "logout", BuildUtils.default_registry]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=10)

    if output.returncode != 0:
        BuildUtils.logger.error("Something went wrong!")
        BuildUtils.logger.error(f"Couldn't logout from registry {BuildUtils.default_registry}")
        BuildUtils.logger.error(f"Message: {output.stdout}")
        BuildUtils.logger.error(f"Error:   {output.stderr}")
        exit(1)

    BuildUtils.logger.info(f"-> Container registry-login: {BuildUtils.default_registry}")
    command = [Container.container_engine, "login", BuildUtils.default_registry, "--username", username, "--password", password]
    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=10)

    if output.returncode != 0:
        BuildUtils.logger.error("Something went wrong!")
        BuildUtils.logger.error(f"Couldn't login into registry {BuildUtils.default_registry}")
        BuildUtils.logger.error(f"Message: {output.stdout}")
        BuildUtils.logger.error(f"Error:   {output.stderr}")
        exit(1)

class BaseImage:
    registry = None
    project = None
    name = None
    version = None
    tag = None
    local_image = None
    present_in_build_tree = None

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
    container_build = None
    container_pushed = None
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

    def __init__(self, dockerfile):
        self.image_name = None
        self.image_version = None
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
        self.container_build = False
        self.container_pushed = False
        self.local_image = False

        if not os.path.isfile(dockerfile):
            BuildUtils.logger.error(f"Dockerfile {dockerfile} not found.")
            if BuildUtils.exit_on_error:
                exit(1)

        with open(dockerfile, 'rt') as f:
            lines = f.readlines()
            for line in lines:

                if line.__contains__('LABEL REGISTRY='):
                    self.registry = line.split("=")[1].rstrip().strip().replace("\"", "")
                elif line.__contains__('LABEL IMAGE='):
                    self.image_name = line.split("=")[1].rstrip().strip().replace("\"", "")
                elif line.__contains__('LABEL VERSION='):
                    self.image_version = line.split("=")[1].rstrip().strip().replace("\"", "")
                elif line.startswith('FROM') and not line.__contains__('#ignore'):
                    base_img_tag = line.split("FROM ")[1].split(" ")[0].rstrip().strip().replace("\"", "")
                    base_img_obj = BaseImage(tag=base_img_tag)
                    if base_img_obj not in self.base_images:
                        self.base_images.append(base_img_obj)
                        if base_img_obj not in BuildUtils.base_images_used:
                            BuildUtils.base_images_used.append(base_img_obj)
                elif line.__contains__('LABEL CI_IGNORE='):
                    self.ci_ignore = True if line.split("=")[1].rstrip().lower().replace("\"", "").replace("'", "") == "true" else False

        if self.image_version == None and self.image_version == "" or self.image_name == None or self.image_name == "":
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
            self.tag = self.registry+"/"+self.image_name+":"+self.image_version
            if "local-only" in self.tag:
                self.local_image = True

    def check_prebuild(self):
        BuildUtils.logger.debug(f"{self.tag}: check_prebuild")
        os.chdir(self.container_dir)
        pre_build_script = os.path.dirname(self.path)+"/pre_build.sh"
        if os.path.isfile(pre_build_script):
            command = [pre_build_script]
            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=3600)

            if output.returncode == 0:
                BuildUtils.logger.debug(f"{self.tag}: pre-build ok.")

            else:
                BuildUtils.logger.error(f"{self.tag}: pre-build failed!")
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name=f"{self.tag}",
                    msg="pre-build failed!",
                    level="ERROR",
                    output=output,
                    path=pre_build_script
                )

        else:
            BuildUtils.logger.debug(f"{self.tag}: no pre-build script!")

    def build(self):
        if Container.enable_build:
            BuildUtils.logger.debug(f"{self.tag}: build")
            if self.container_pushed:
                BuildUtils.logger.debug(f"{self.tag}: already build -> skip")
                return

            startTime = time()
            os.chdir(self.container_dir)
            if BuildUtils.http_proxy is not None:
                command = [Container.container_engine, "build", "--build-arg", f"http_proxy={BuildUtils.http_proxy}",
                           "--build-arg", f"https_proxy={BuildUtils.http_proxy}", "-t", self.tag, "-f", self.path, "."]
            else:
                command = [Container.container_engine, "build", "-t", self.tag, "-f", self.path, "."]

            output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=6000, env=dict(os.environ, DOCKER_BUILDKIT=f"{BuildUtils.enable_build_kit}"))

            if output.returncode != 0:
                BuildUtils.logger.error(f"{self.tag}: build failed!")
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name=f"{self.tag}",
                    msg="container build failed!",
                    level="ERROR",
                    output=output,
                    path=self.container_dir
                )
            else:
                self.already_built = True
                hours, rem = divmod(time()-startTime, 3600)
                minutes, seconds = divmod(rem, 60)
                BuildUtils.logger.info("{}: Build-time: {:0>2}:{:0>2}:{:05.2f}".format(self.tag, int(hours), int(minutes), seconds))
                self.container_build = True
        else:
            BuildUtils.logger.debug(f"{self.tag}: build disabled")

    def push(self, retry=True):
        if Container.enable_push:
            if not self.local_image:
                BuildUtils.logger.debug(f"{self.tag}: push")
                if self.container_pushed:
                    BuildUtils.logger.debug(f"{self.tag}: already pushed -> skip")
                    return
                
                if not self.container_build:
                    BuildUtils.logger.warning(f"{self.tag}: push skipped -> container not build!")
                    BuildUtils.generate_issue(
                        component=suite_tag,
                        name=f"{self.tag}",
                        msg="Push skipped -> container not build!",
                        level="WARNING",
                        path=self.container_dir
                    )

                max_retires = 2
                retries = 0

                command = [Container.container_engine, "push", self.tag]

                while retries < max_retires:
                    retries += 1
                    output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=9000)
                    if output.returncode == 0 or "configured as immutable" in output.stderr:
                        break

                if output.returncode == 0 and ("Pushed" in output.stdout or "podman" in Container.container_engine):
                    BuildUtils.logger.info(f"{self.tag}: pushed")
                    self.container_pushed = True

                if output.returncode == 0:
                    BuildUtils.logger.info(f"{self.tag}: pushed -> nothing was changed.")
                    self.container_pushed = True

                elif output.returncode != 0 and "configured as immutable" in output.stderr:
                    BuildUtils.logger.info(f"{self.tag}: not pushed -> immutable!")
                    self.container_pushed = True

                elif output.returncode != 0 and "read only mode" in output.stderr and retry:
                    BuildUtils.logger.info(f"{self.tag}: not pushed -> read only mode!")
                    self.container_pushed = True

                elif output.returncode != 0 and "denied" in output.stderr and retry:
                    BuildUtils.logger.error(f"{self.tag}: not pushed -> access denied!")
                    BuildUtils.generate_issue(
                        component=suite_tag,
                        name=f"{self.tag}",
                        msg="container pushed failed!",
                        level="ERROR",
                        output=output,
                        path=self.container_dir
                    )
                else:
                    BuildUtils.logger.error(f"{self.tag}: not pushed -> unknown reason!")
                    BuildUtils.generate_issue(
                        component=suite_tag,
                        name=f"{self.tag}",
                        msg="container pushed failed!",
                        level="ERROR",
                        output=output,
                        path=self.container_dir
                    )
            else:
                BuildUtils.logger.debug(f"{self.tag}: push skipped -> local registry found")
        else:
            BuildUtils.logger.debug(f"{self.tag}: push disabled")

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
            BuildUtils.logger.warning("")
            BuildUtils.logger.warning("-> Duplicate Dockerfiles found!")

        dockerfiles_found = set(dockerfiles_found)

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
            container.missing_base_images = []
            for base_image in container.base_images:
                if base_image.local_image and base_image.tag not in Container.container_object_list:
                    container.missing_base_images.append(base_image)
                    BuildUtils.logger.error("")
                    BuildUtils.logger.error(f"-> {container.container_id} - base_image missing: {base_image.tag}")
                    BuildUtils.logger.error("")
                    if BuildUtils.exit_on_error:
                        exit(1)

        return container_object_list


if __name__ == '__main__':
    print("Please use the 'start_build.py' script to launch the build-process.")
    exit(1)
