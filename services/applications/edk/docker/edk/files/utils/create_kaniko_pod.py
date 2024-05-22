import argparse
import yaml
import shutil
import os
from datetime import datetime
import threading
from typing import List, Dict, Any, Union
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

# kube config
config.load_incluster_config()
v1 = client.CoreV1Api()

# env vars
NAMESPACE = os.getenv("NAMESPACE", None)
assert NAMESPACE is not None, "ERROR: env variable NAMESPACE can not be empty"

SHARED_VOLUME_PATH = os.getenv("VOLUME_PATH", None)
assert (
    SHARED_VOLUME_PATH is not None
), "ERROR: env variable SHARED_VOLUME_PATH can not be empty"

LOCAL_REGISTRY_URL = os.getenv("LOCAL_REGISTRY_URL", None)
assert NAMESPACE is not None, "ERROR: env variable LOCAL_REGISTRY_URL can not be empty"


def get_image_info(dockerfile_path: str) -> tuple[str, str]:
    # expects LABEL IMAGE="<image-name>" and LABEL VERSION="<label-version>" to be present in Dockerfile
    name = ""
    version = ""
    with open(dockerfile_path, "r") as file:
        for line in file:
            if line.startswith("LABEL IMAGE="):
                name = line.split("=")[-1].strip().strip('"')
            elif line.startswith("LABEL VERSION="):
                version = line.split("=")[-1].strip().strip('"')
    if name == "":
        raise ValueError(
            f"'LABEL IMAGE=' line not found in Dockerfile {dockerfile_path}"
        )
    if version == "":
        raise ValueError(
            f"'LABEL VERSION=' line not found in Dockerfile {dockerfile_path}"
        )

    return name, version


# TODO: this is not necessary unless entire kaapana is being built, just add a template Dockerfile with FROM <registry_url>/base-python-cpu
# TODO: might be necessary when building base-python-gpu based on base-python-cpu
def edit_dockerfile(dockerfile_path: str, reg_url: str) -> None:
    with open(dockerfile_path, "r") as file:
        lines = file.readlines()

    with open(dockerfile_path, "w") as file:
        for line in lines:
            if line.startswith("FROM local-only/"):
                # TODO
                pass


def make_pod_yaml(
    yaml_file: str,
    dockerfile: str,
    context: str,
    image_name: str = "",
    image_version: str = "",
) -> tuple[Any, str, str]:
    with open(yaml_file, "r") as f:
        pod_yaml = yaml.safe_load(f)

    # get image info if not passed
    if image_name == "" or image_version == "":
        f_image_name, f_image_version = get_image_info(dockerfile)
        image_name = f_image_name if image_name == "" else image_name
        image_version = f_image_version if image_version == "" else image_version
    pod_yaml["metadata"][
        "name"
    ] += f"-{image_name}-{image_version}-" + datetime.now().strftime("%Y%m%d%H%M%S")

    # copy Dockerfile & context dir to shared volume
    dest_dir = copy_files(dockerfile, context, image_name)

    # update kaniko parameters in pod yaml
    for i, arg in enumerate(pod_yaml["spec"]["containers"][0]["args"]):
        if "--dockerfile=" in arg:
            pod_yaml["spec"]["containers"][0]["args"][
                i
            ] = f"--dockerfile={dest_dir}/Dockerfile"
        elif "--context=dir://" in arg:
            pod_yaml["spec"]["containers"][0]["args"][i] = f"--context=dir://{dest_dir}"
        elif "--destination=" in arg:
            pod_yaml["spec"]["containers"][0]["args"][
                i
            ] = f"--destination={LOCAL_REGISTRY_URL}/{image_name}:{image_version}"

    return pod_yaml, image_name, dest_dir


def copy_files(dockerfile: str, context: str, image_name: str) -> str:
    dest_dir = f"{SHARED_VOLUME_PATH}/{image_name}"
    os.makedirs(dest_dir, exist_ok=True)

    # copy Dockerfile
    shutil.copy(dockerfile, os.path.join(dest_dir, "Dockerfile"))

    # copy context dir
    for item in os.listdir(context):
        s = os.path.join(context, item)
        d = os.path.join(dest_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)

    print(f"Dockerfile and context dir copied to {dest_dir}")
    return dest_dir


def create_pod(pod_yaml: Dict[str, Any]) -> None:
    v1.create_namespaced_pod(namespace=NAMESPACE, body=pod_yaml)
    print("Pod created successfully")


def delete_files(dest_dir: str) -> None:
    try:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)
            print(f"Deleted directory {dest_dir}")
    except Exception as e:
        print(f"Failed to delete files in {dest_dir}: {e}")


def monitor_pod(pod_name: str, dest_dir: str) -> None:
    w = watch.Watch()
    print(f"watching pod {pod_name}")
    for event in w.stream(v1.list_namespaced_pod, namespace=NAMESPACE):
        if isinstance(event, dict):
            event_type: Union[str, None] = event.get("type")
            pod: Union[client.V1Pod, None] = event.get("object")
            if isinstance(pod, client.V1Pod):
                pod_metadata = pod.metadata
                pod_status = pod.status
                if pod_metadata and pod_metadata.name == pod_name:
                    if event_type == "ADDED":
                        print(f"Pod {pod_name} added")
                    if event_type == "DELETED":
                        print(f"Pod {pod_name} deleted unexpectedly")
                    if pod_status:
                        if pod_status.phase in ["Failed", "Succeeded"]:
                            print(
                                f"Pod {pod_name} finished with status: {pod_status.phase}, deleting files at {dest_dir}"
                            )
                            delete_files(dest_dir)
                            return
                        else:
                            print(f"Pod {pod_name} status: {pod_status.phase}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a Kaniko builder pod under the same namespace"
    )
    parser.add_argument(
        "yaml_file", type=str, help="The YAML file to use as a template"
    )
    parser.add_argument(
        "--dockerfile", type=str, required=True, help="The path to the Dockerfile"
    )
    parser.add_argument(
        "--context", type=str, required=True, help="The build context directory"
    )
    parser.add_argument(
        "--image_name",
        type=str,
        default="",
        help="Image name, if empty the LABEL inside Dockerfile is used",
    )
    parser.add_argument(
        "--image_version",
        type=str,
        default="",
        help="Image version, if empty the LABEL inside Dockerfile is used",
    )

    args = parser.parse_args()

    pod_yaml, image_name, dest_dir = make_pod_yaml(
        args.yaml_file,
        args.dockerfile,
        args.context,
        args.image_name,
        args.image_version,
    )

    # create kaniko builder pod
    create_pod(pod_yaml)

    pod_name = pod_yaml["metadata"]["name"]

    # monitor pod, delete files when finished
    monitor_pod(pod_name, dest_dir)
