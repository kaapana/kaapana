import argparse
import yaml
import shutil
import os
from kubernetes import client, config

# TODO: rm context dir from shared folder once pod terminates

def get_image_name(dockerfile_path):
    with open(dockerfile_path, "r") as file:
        for line in file:
            if line.startswith("LABEL IMAGE="):
                return line.split("=")[-1].strip().strip('"')
    raise ValueError(f"'LABEL IMAGE=' line not found in Dockerfile {dockerfile_path}")


def make_pod_yaml(yaml_file, dockerfile, context, dest):
    with open(yaml_file, "r") as f:
        pod_yaml = yaml.safe_load(f)

    # update pod name
    image_name = get_image_name(dockerfile)
    pod_yaml["metadata"]["name"] += f"-{image_name}"

    # update yaml
    for i, arg in enumerate(pod_yaml["spec"]["containers"][0]["args"]):
        if "--dockerfile=" in arg:
            pod_yaml["spec"]["containers"][0]["args"][
                i
            ] = f"--dockerfile=/kaapana/app/edk-data/{image_name}/Dockerfile"
        elif "--context=dir://" in arg:
            pod_yaml["spec"]["containers"][0]["args"][
                i
            ] = f"--context=dir:///kaapana/app/edk-data/{image_name}"
        elif "--destination=" in arg:
            pod_yaml["spec"]["containers"][0]["args"][i] = f"--destination={dest}"

    return pod_yaml, image_name


def copy_files(dockerfile, context, image_name):
    dest_dir = f"/kaapana/app/edk-data/{image_name}"
    os.makedirs(dest_dir, exist_ok=True)

    # cp dockerfile
    shutil.copy(dockerfile, os.path.join(dest_dir, "Dockerfile"))

    # cp context dir
    for item in os.listdir(context):
        s = os.path.join(context, item)
        d = os.path.join(dest_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)

    print(f"Dockerfile and context dir copied to {dest_dir}")


def create_pod(pod_yaml):
    config.load_incluster_config()

    v1 = client.CoreV1Api()
    v1.create_namespaced_pod(namespace="services", body=pod_yaml)
    print("Pod created successfully")


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
        "--dest", type=str, required=True, help="The destination image registry"
    )

    args = parser.parse_args()

    pod_yaml, image_name = make_pod_yaml(
        args.yaml_file, args.dockerfile, args.context, args.dest
    )

    # copy Dockerfile & context dir to shared volume
    copy_files(args.dockerfile, args.context, image_name)

    # create kaniko builder pod
    create_pod(pod_yaml)
