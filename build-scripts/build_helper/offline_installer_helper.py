
import os
import json
from subprocess import PIPE, run
from os.path import join, dirname, basename, exists, isfile, isdir
from build_helper.build_utils import BuildUtils
from build_helper.container_helper import Container, pull_container_image
from alive_progress import alive_bar
from shutil import copyfile

class OfflineInstallerHelper:
    SNAP_DOWNLOAD_TIMEOUT = 120
    HELM_DOWNLOAD_TIMEOUT = 10
    IMAGE_SAVE_TIMEOUT = 6000
    
    @staticmethod
    def download_gpu_operator_chart(target_path):
        BuildUtils.logger.info(f"Downloading gpu-operator helm chart ...")
        command = ["helm","repo","add","nvidia","https://nvidia.github.io/gpu-operator"]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=OfflineInstallerHelper.HELM_DOWNLOAD_TIMEOUT)
        if output.returncode != 0 and "already exists" not in output.stderr:
            BuildUtils.logger.error(f"Helm download gpu-operator {output.stderr}!")
            BuildUtils.generate_issue(
                component="Helm repo add",
                name=f"Helm repo add NVIDIA",
                msg=f"Helm failed {output.stderr}!",
                level="ERROR"
            )
        command = ["helm", "repo", "update"]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=OfflineInstallerHelper.HELM_DOWNLOAD_TIMEOUT)
        if output.returncode != 0:
            BuildUtils.logger.error(f"Helm repo update {output.stderr}!")
            BuildUtils.generate_issue(
                component="Helm repo update",
                name=f"Helm repo update",
                msg=f"Helm repo update failed {output.stderr}!",
                level="ERROR"
            )
        
        name="nvidia/gpu-operator"
        version="v22.9.2"
        command = ["helm","pull",name, f"--version={version}",f"--destination={target_path}"]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=OfflineInstallerHelper.HELM_DOWNLOAD_TIMEOUT)
        if output.returncode != 0:
            BuildUtils.logger.error(f"Helm download {name} {output.stderr}!")
            BuildUtils.generate_issue(
                component="Helm download",
                name=f"Helm download {name}",
                msg=f"Helm download failed {output.stderr}!",
                level="ERROR"
            )
        else:
            helm_chart_path = join(target_path,f"gpu-operator-{version}.tgz")
            new_helm_chart_path = join(target_path,"gpu-operator.tgz")
            assert exists(helm_chart_path)
            os.rename(helm_chart_path,new_helm_chart_path)

    @staticmethod
    def download_snap_package(name,version,target_path):
        BuildUtils.logger.info(f"Downloading {name} snap package ...")
        command = ["snap","download",name,f"--target-directory={target_path}",f"--channel={version}"]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=OfflineInstallerHelper.SNAP_DOWNLOAD_TIMEOUT)
        if output.returncode != 0:
            BuildUtils.logger.error(f"Snap download {name} {output.stderr}!")
            BuildUtils.generate_issue(
                component="Snap download",
                name=f"Snap download {name}",
                msg=f"Snap download failed {output.stderr}!",
                level="ERROR"
            )
        else:
            snap_filename = output.stdout.split("/")[-1].strip()
            snap_version = snap_filename.split("_")[-1].split(".")[0]
            snap_file_path = join(target_path,snap_filename)
            assert exists(snap_file_path)
            os.rename(snap_file_path,snap_file_path.replace(f"_{snap_version}",""))

            assert_file_path = join(target_path,f"{name}_{snap_version}.assert")
            assert exists(assert_file_path)
            os.rename(assert_file_path,assert_file_path.replace(f"_{snap_version}",""))


    @staticmethod
    def export_image_list_into_tarball(image_list,images_tarball_path,timeout=600):
        BuildUtils.logger.info(f"Exporting images as tarball @{images_tarball_path} ...")
        BuildUtils.logger.warn(f"This can take a long time! -> please be patient and wait.")
        command = [Container.container_engine, "save"] + [build_tag for build_tag in image_list if not build_tag.startswith('local-only')] + ["-o", images_tarball_path]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=timeout)
        if output.returncode != 0:
            BuildUtils.logger.error(f"Docker save failed {output.stderr}!")
            BuildUtils.generate_issue(
                component="docker save",
                name="Docker save",
                msg=f"Docker save failed {output.stderr}!",
                level="ERROR"
            )

    @staticmethod
    def generate_microk8s_offline_version():
        microk8s_offline_installer_target_dir=join(BuildUtils.build_dir,"microk8s-offline-installer")
        BuildUtils.logger.info("Generating Microk8s offline installer...")

        DEFAULT_CORE_VERSION="latest/stable"
        OfflineInstallerHelper.download_snap_package(name="core18",version=DEFAULT_CORE_VERSION,target_path=microk8s_offline_installer_target_dir)
        
        DEFAULT_MICRO_VERSION="1.26/stable"
        OfflineInstallerHelper.download_snap_package(name="microk8s",version=DEFAULT_MICRO_VERSION,target_path=microk8s_offline_installer_target_dir)
        
        DEFAULT_HELM_VERSION="latest/stable"
        OfflineInstallerHelper.download_snap_package(name="helm",version=DEFAULT_HELM_VERSION,target_path=microk8s_offline_installer_target_dir)
        
        OfflineInstallerHelper.download_gpu_operator_chart(target_path=microk8s_offline_installer_target_dir)

        micok8s_base_img_json_path = join(BuildUtils.kaapana_dir,"build-scripts","build_helper","microk8s_images.json")
        assert exists(micok8s_base_img_json_path)
        with open(micok8s_base_img_json_path, encoding='utf-8') as f:
            microk8s_base_images = json.load(f)["microk8s_base_images"]

        images_tarball_path = join(microk8s_offline_installer_target_dir,"microk8s_base_images.tar")
        BuildUtils.logger.info("Pulling base images ...")
        with alive_bar(len(microk8s_base_images), dual_line=True, title='Pull Microk8s base-images') as bar:
            for base_microk8s_image in microk8s_base_images:
                bar.text(f"Pull: {base_microk8s_image}")
                pull_container_image(image_tag=str(base_microk8s_image))
                bar()
        OfflineInstallerHelper.export_image_list_into_tarball(image_list=microk8s_base_images,images_tarball_path=images_tarball_path)
        
        server_install_script_path = join(BuildUtils.kaapana_dir,"server-installation","server_installation.sh")
        assert exists(server_install_script_path)
        dst_script_path =join(microk8s_offline_installer_target_dir,basename(server_install_script_path))
        copyfile(src=server_install_script_path,dst=dst_script_path)
        os.chmod(dst_script_path, 0o775)

        offline_enable_gpu_script_path = join(BuildUtils.kaapana_dir,"server-installation","offline_enable_gpu.py")
        assert exists(offline_enable_gpu_script_path)
        dst_script_path =join(microk8s_offline_installer_target_dir,basename(offline_enable_gpu_script_path))
        copyfile(src=offline_enable_gpu_script_path,dst=dst_script_path)
        os.chmod(offline_enable_gpu_script_path, 0o775)

        BuildUtils.logger.info("Finished: Generating Microk8s offline installer.")
