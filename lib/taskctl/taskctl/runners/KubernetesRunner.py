import json
import base64
import re
import datetime

from kubernetes import client, config, watch
from taskctl.processing_container.models import Task, TaskRun, TaskInstance
from taskctl.processing_container.resources import compute_memory_resources
from taskctl.processing_container.common import (
    create_task_instance,
    get_processing_container,
)
from taskctl.runners.base import BaseRunner

from typing import Tuple, List


def sanitize_name(name: str) -> str:
    # lowercase and replace invalid chars
    return re.sub(r"[^a-z0-9.-]", "-", name.lower())


def generate_pod_name(base_name: str) -> str:
    sanitized = sanitize_name(base_name)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    return f"task-{sanitized[:50]}-{timestamp}"  # truncate base if needed


def get_volume_and_mounts(
    task_instance: TaskInstance,
) -> Tuple[List[client.V1Volume], List[client.V1VolumeMount]]:
    volumes = []
    volume_mounts = []
    mount_paths = []

    for channel in [*task_instance.inputs, *task_instance.outputs]:
        if channel.mounted_path in mount_paths:
            continue
        mount_paths.append(channel.mounted_path)
        name = f"vol-{channel.name}"
        volumes.append(
            client.V1Volume(
                name=name,
                host_path=client.V1HostPathVolumeSource(path=channel.input.local_path),
            )
        )
        volume_mounts.append(
            client.V1VolumeMount(name=name, mount_path=channel.mounted_path)
        )
    return volumes, volume_mounts


def get_container(
    task_instance: TaskInstance, volume_mounts: List[client.V1VolumeMount]
) -> client.V1Container:
    env_vars = [
        client.V1EnvVar(name=env.name, value=env.value) for env in task_instance.env
    ]
    return client.V1Container(
        name="main",
        image=task_instance.image,
        command=task_instance.command,
        env=env_vars,
        volume_mounts=volume_mounts,
        resources=client.V1ResourceRequirements(
            limits=(
                task_instance.resources.limits.model_dump(exclude_none=True)
                if task_instance.resources.limits
                else None
            ),
            requests=(
                task_instance.resources.requests.model_dump(exclude_none=True)
                if task_instance.resources.requests
                else None
            ),
        ),
    )


class KubernetesRunner(BaseRunner):
    config.load_config()
    api = client.CoreV1Api()

    @classmethod
    def run(cls, task: Task, dry_run: bool = False):
        cls._logger.info("Running task in Kubernetes...")
        mode = "k8s" if not dry_run else "docker"
        processing_container = get_processing_container(task.image, mode=mode)
        task_instance = create_task_instance(
            processing_container=processing_container, task=task
        )

        pod_name = generate_pod_name(task_instance.name)
        volumes, volume_mounts = get_volume_and_mounts(task_instance)
        task_instance.resources = compute_memory_resources(task_instance)
        task_container = get_container(
            task_instance=task_instance, volume_mounts=volume_mounts
        )
        if dry_run:
            image_pull_secrets = []
        else:
            image_pull_secrets = cls.get_image_pull_secrets(task_instance)

        pod_spec = client.V1PodSpec(
            restart_policy="Never",
            containers=[task_container],
            volumes=volumes,
            image_pull_secrets=image_pull_secrets,
        )

        pod = client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=pod_name, labels={"kaapana.type": "processing-container"}
            ),
            spec=pod_spec,
        )

        # push pod to Kubernetes
        cls._logger.info(
            f"Creating pod '{pod_name}' in namespace '{task_instance.namespace}'..."
        )

        if dry_run:
            id = "dummy-id"
        else:
            pod = cls.api.create_namespaced_pod(
                namespace=task_instance.namespace, body=pod
            )
            task_instance.imagePullSecrets = [
                secret.name for secret in pod.spec.image_pull_secrets
            ]
            id = pod.metadata.name
        return TaskRun(
            id=id,
            mode=mode,
            **task_instance.model_dump(),
        )

    @classmethod
    def logs(cls, task_run: TaskRun, follow: bool):
        """
        Log stdout and stderr of the container corresponding to task_run.
        """
        cls._logger.debug("Waiting for pod to start running...")
        w = watch.Watch()

        # Wait until pod is in Running state
        cls.wait_for_task_status(
            task_run=task_run,
            states=["Running", "Succeeded", "Failed"],
            timeout=30,
        )

        cls._logger.debug("Streaming logs from the pod container...")
        try:
            logs = cls.api.read_namespaced_pod_log(
                name=task_run.id,
                namespace=task_run.namespace,
                container="main",
                follow=follow,
                _preload_content=False,
                _return_http_data_only=True,
                pretty=True,
            )

            for line in logs:
                cls._logger.info(line.decode("utf-8").rstrip())

        except Exception as e:
            cls._logger.error(f"Error while streaming logs: {e}")
            raise e

    @classmethod
    def stop(cls, task_run: TaskRun):
        config.load_config()
        cls.api.delete_namespaced_pod(name=task_run.id, namespace=task_run.namespace)

    @classmethod
    def wait_for_task_status(
        cls,
        task_run: TaskRun,
        states: list = ["Running", "Succeeded", "Failed"],
        timeout: int = 5,
    ):
        """ """
        w = watch.Watch()

        for event in w.stream(
            cls.api.list_namespaced_pod,
            namespace=task_run.namespace,
            field_selector=f"metadata.name={task_run.id}",
            timeout_seconds=timeout,
        ):
            pod_obj = event["object"]
            if pod_obj.status.phase in states:
                cls._logger.debug(f"Pod entered phase: {pod_obj.status.phase}")
                w.stop()
                return
            else:
                cls._logger.warning(f"Pod in phase: {pod_obj.status.phase}")
        raise TimeoutError(
            f"Pod {task_run.id} in namespace {task_run.namespace} did not reach one of the states {states} in {timeout} seconds."
        )

    @classmethod
    def create_image_pull_secret(
        cls, task_instance: TaskInstance, secret_name: str
    ) -> client.V1Secret:
        """
        Create a secret derived from registryUrl, registryUsername, registryPassword
        that can be used as ImagePullSecret
        """
        cls._logger.info("Creating image pull secret...")

        reg_config_json = {
            "auths": {
                task_instance.registryUrl: {
                    "username": task_instance.registryUsername,
                    "password": task_instance.registryPassword,
                    "auth": base64.b64encode(
                        f"{task_instance.registryUsername}:{task_instance.registryPassword}".encode()
                    ).decode(),
                }
            }
        }

        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(name=secret_name),
            type="kubernetes.io/dockerconfigjson",
            data={
                ".dockerconfigjson": base64.b64encode(
                    json.dumps(reg_config_json).encode()
                ).decode()
            },
        )

        cls.api.create_namespaced_secret(namespace=task_instance.namespace, body=secret)
        return secret

    @classmethod
    def get_image_pull_secrets(
        cls, task_instance: TaskInstance
    ) -> List[client.V1LocalObjectReference]:

        image_pull_secrets = []

        if (
            task_instance.registryUrl
            and task_instance.registryUsername
            and task_instance.registryPassword
        ):
            secret_name = f"{generate_pod_name(task_instance.name)}-secret"
            cls.create_image_pull_secret(task_instance, secret_name)
            image_pull_secrets.append(client.V1LocalObjectReference(name=secret_name))
        elif task_instance.imagePullSecrets:
            image_pull_secrets.extend(
                [
                    client.V1LocalObjectReference(name=name)
                    for name in task_instance.imagePullSecrets
                ]
            )
        return image_pull_secrets
