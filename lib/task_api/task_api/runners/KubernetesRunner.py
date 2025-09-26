import json
import base64
import re
import datetime
import time

from kubernetes import client, config, watch
from task_api.processing_container import task_models, pc_models
from task_api.processing_container.resources import compute_memory_resources
from task_api.processing_container.common import (
    create_task_instance,
    get_task_template,
)
from task_api.runners.base import BaseRunner

from typing import Tuple, List


def generate_pod_name(base_name: str) -> str:
    """
    Generate a valid Kubernetes pod name from an arbitrary string.

    Rules enforced:
    - Lowercase only
    - Allowed characters: [a-z0-9-.]
    - Must start and end with alphanumeric
    - Max length: 62 chars -> dcmsend does not work if local hostname is too long
    """

    sanitized_name = base_name.lower()
    sanitized_name = re.sub(r"[^a-z0-9.-]", "-", sanitized_name)
    sanitized_name = re.sub(r"^[^a-z0-9]+", "", sanitized_name)
    sanitized_name = re.sub(r"[^a-z0-9]+$", "", sanitized_name)
    if len(sanitized_name) > 62:
        sanitized_name = sanitized_name[:62]
        # after cutting, re-strip trailing non-alphanumeric
        sanitized_name = re.sub(r"[^a-z0-9]+$", "", sanitized_name)

    return sanitized_name


def get_volume_and_mounts(
    task_instance: task_models.TaskInstance,
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
                host_path=client.V1HostPathVolumeSource(path=channel.input.host_path),
            )
        )
        volume_mounts.append(
            client.V1VolumeMount(name=name, mount_path=channel.mounted_path)
        )
    return volumes, volume_mounts


def get_container(
    task_instance: task_models.TaskInstance, volume_mounts: List[client.V1VolumeMount]
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
            limits=task_instance.resources.limits,
            requests=task_instance.resources.requests,
        ),
    )


class KubernetesRunner(BaseRunner):
    config.load_config()
    api = client.CoreV1Api()

    @classmethod
    def run(cls, task: task_models.Task, dry_run: bool = False):
        """
        Create and execute a Kubernetes Pod for the given task.

        This method translates a task definition into a Kubernetes Pod spec,
        applies resource and configuration settings, and submits it to the
        cluster via the Kubernetes API. The resulting Pod runs the specified
        task container in `Never` restart mode.

        Workflow:
            1. Resolve image pull secrets and task template.
            2. Create a task instance and derive pod/container configuration.
            3. Compute resource requirements, volumes, and environment variables.
            4. Construct the Kubernetes Pod manifest.
            5. Submit the Pod to the cluster namespace.
            6. Return a `TaskRun` object representing the execution.

        Args:
            task (task_models.Task):
                The task definition, including image, configuration,
                volumes, environment variables, and template reference.
            dry_run (bool):
                If True, build the Pod specification without submitting it
                to Kubernetes. Currently unused in this implementation.

        Returns:
            task_models.TaskRun:
                A task run object containing the Pod name as the run ID,
                execution mode, and metadata derived from the task instance.

        Raises:
            kubernetes.client.exceptions.ApiException:
                If creating the Pod in Kubernetes fails.
            ValueError:
                If the task template cannot be resolved.
        """
        cls._logger.info("Running task in Kubernetes...")

        image_pull_secrets = cls.get_image_pull_secrets(task)
        imagePullSecrets = [secret.name for secret in image_pull_secrets]

        if isinstance(task.taskTemplate, pc_models.TaskTemplate):
            task_template = task.taskTemplate
        else:
            task_template = get_task_template(
                image=task.image,
                task_identifier=task.taskTemplate,
                namespace=task.config.namespace,
                registry_secret=imagePullSecrets[0],
                mode="k8s",
            )

        task_instance = create_task_instance(task_template=task_template, task=task)
        pod_name = generate_pod_name(task_instance.name)
        volumes, volume_mounts = get_volume_and_mounts(task_instance)
        volumes.extend(task_instance.config.volumes)
        volume_mounts.extend(task_instance.config.volume_mounts)
        task_instance.resources = compute_memory_resources(task_instance)
        task_container = get_container(
            task_instance=task_instance, volume_mounts=volume_mounts
        )
        task_container.env = task_container.env + task_instance.config.env_vars

        pod_spec = client.V1PodSpec(
            restart_policy="Never",
            containers=[task_container],
            volumes=volumes,
            image_pull_secrets=image_pull_secrets,
        )

        pod = client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=pod_name, labels=task_instance.config.labels
            ),
            spec=pod_spec,
        )
        task_instance.config.V1Pod = pod

        if dry_run:
            cls._logger.info(f"Pod was not created in Kubernetes because {dry_run=}.")
            return task_models.TaskRun(
                id="dry-run",
                mode="k8s",
                **task_instance.model_dump(),
            )

        # push pod to Kubernetes
        cls._logger.info(
            f"Creating pod '{pod_name}' in namespace '{task_instance.config.namespace}'..."
        )
        pod = cls.api.create_namespaced_pod(
            namespace=task_instance.config.namespace, body=pod
        )
        id = pod.metadata.name
        return task_models.TaskRun(
            id=id,
            mode="k8s",
            **task_instance.model_dump(),
        )

    @classmethod
    def logs(
        cls,
        task_run: task_models.TaskRun,
        follow: bool = True,
        startup_timeout: int = 30,
        log_timeout: int = 3600,
    ):
        """
        Log stdout and stderr of the container corresponding to task_run.

        Log stdout and stderr of the container corresponding to task_run.

        Args:
            task_run: TaskRun object containing pod metadata.
            follow (bool): Whether to stream logs continuously.
            startup_timeout (int): Time in seconds to wait for pod to start running.
            log_timeout (int): Max time in seconds to stream logs before raising TimeoutError.
        """
        cls._logger.debug("Waiting for pod to start running...")
        w = watch.Watch()

        # Wait until pod is in Running state
        cls.wait_for_task_status(
            task_run=task_run,
            states=["Running", "Succeeded", "Failed"],
            timeout=startup_timeout,
        )

        start_time = time.time()

        cls._logger.debug("Streaming logs from the pod container...")
        try:
            logs = cls.api.read_namespaced_pod_log(
                name=task_run.id,
                namespace=task_run.config.namespace,
                container="main",
                follow=follow,
                _preload_content=False,
                _return_http_data_only=True,
                pretty=True,
            )

            for line in logs:
                if abs(time.time() - start_time) > log_timeout:
                    cls._logger.error(
                        f"Log streaming exceeded timeout of {log_timeout}s for pod {task_run.id}"
                    )
                    raise TimeoutError(
                        f"Log streaming exceeded timeout of {log_timeout}s"
                    )

                cls._logger.info(line.decode("utf-8").rstrip())

        except TimeoutError:
            raise
        except Exception as e:
            cls._logger.error(f"Error while streaming logs: {e}")
            raise e

    @classmethod
    def stop(cls, task_run: task_models.TaskRun):
        config.load_config()
        cls.api.delete_namespaced_pod(
            name=task_run.id, namespace=task_run.config.namespace
        )

    @classmethod
    def wait_for_task_status(
        cls,
        task_run: task_models.TaskRun,
        states: list = ["Running", "Succeeded", "Failed"],
        timeout: int = 5,
    ) -> str:
        """ """
        w = watch.Watch()

        for event in w.stream(
            cls.api.list_namespaced_pod,
            namespace=task_run.config.namespace,
            field_selector=f"metadata.name={task_run.id}",
            timeout_seconds=timeout,
        ):
            pod_obj = event["object"]
            if pod_obj.status.phase in states:
                cls._logger.debug(f"Pod entered phase: {pod_obj.status.phase}")
                w.stop()
                return pod_obj.status.phase
            else:
                cls._logger.warning(f"Pod in phase: {pod_obj.status.phase}")
        raise TimeoutError(
            f"Pod {task_run.id} in namespace {task_run.config.namespace} did not reach one of the states {states} in {timeout} seconds."
        )

    @classmethod
    def create_image_pull_secret(
        cls, task: task_models.Task, secret_name: str
    ) -> client.V1Secret:
        """
        Create a secret derived from registryUrl, registryUsername, registryPassword
        that can be used as ImagePullSecret
        """
        cls._logger.info("Creating image pull secret...")

        reg_config_json = {
            "auths": {
                task.config.registryUrl: {
                    "username": task.config.registryUsername,
                    "password": task.config.registryPassword,
                    "auth": base64.b64encode(
                        f"{task.config.registryUsername}:{task.config.registryPassword}".encode()
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
        try:
            cls.api.create_namespaced_secret(
                namespace=task.config.namespace, body=secret
            )
        except client.ApiException as e:
            if e.status == 409 or e.reason == "Conflict":
                cls._logger.warning(
                    f"Secret {secret_name} already exists in namespace {task.config.namespace}."
                )
        return secret

    @classmethod
    def get_image_pull_secrets(
        cls, task: task_models.Task
    ) -> List[client.V1LocalObjectReference]:
        image_pull_secrets = []
        if (
            task.config.registryUrl
            and task.config.registryUsername
            and task.config.registryPassword
        ):
            secret_name = f"{generate_pod_name(task.name)}-secret"
            cls.create_image_pull_secret(task, secret_name)
            image_pull_secrets.append(client.V1LocalObjectReference(name=secret_name))
        if task.config.imagePullSecrets:
            image_pull_secrets.extend(
                [
                    client.V1LocalObjectReference(name=name)
                    for name in task.config.imagePullSecrets
                ]
            )
        return image_pull_secrets
