import functools
import json
from task_api.processing_container import models
from typing import List
from pathlib import Path
from jinja2 import Environment, BaseLoader
import os


def _parse_with_jinja(file: Path, custom_vars: dict = {}) -> dict:
    jinja_env = Environment(loader=BaseLoader())
    jinja_env.globals["env"] = os.environ

    with open(file, "r") as f:
        task_text = f.read()

    template = jinja_env.from_string(task_text)
    rendered = template.render(custom=custom_vars)

    return json.loads(rendered)


def parse_task(file: Path, custom_vars: dict = {}) -> models.Task:
    """
    Parse a json file to a Task object and use jinja templating.
    """
    return models.Task(**_parse_with_jinja(file, custom_vars=custom_vars))


def parse_processing_container(
    file: Path, custom_vars: dict = {}
) -> models.ProcessingContainer:
    """
    Parse a json file to a ProcessingContainer object and use jinja templating.
    """

    return models.ProcessingContainer(
        **_parse_with_jinja(file, custom_vars=custom_vars)
    )


def create_task_instance(
    task_template: models.TaskTemplate, task: models.Task
) -> models.TaskInstance:
    """
    Create a TaskInstance object by merging a TaskTemplate and a Task object
    """
    return models.TaskInstance(
        inputs=merge_io_channels(task_template.inputs, task.inputs),
        outputs=merge_io_channels(task_template.outputs, task.outputs),
        env=merge_env(task_template.env, task.env),
        **{
            **task_template.model_dump(
                mode="python", exclude=["inputs", "outputs", "env"], exclude_none=True
            ),
            **task.model_dump(
                mode="python", exclude=["inputs", "outputs", "env"], exclude_none=True
            ),
        },
    )


def merge_env(
    orig_envs: List[models.ContainerEnvVar], update_envs: List[models.ContainerEnvVar]
) -> List[models.ContainerEnvVar]:
    """
    Merge two lists of ContainerEnvVar objects.

    If two objects from both lists share the same name,
    overwrite values from the object in <orig_envs> with values from the object in <update_envs>.
    """
    orig_names = [env.name for env in orig_envs]
    update_names = [env.name for env in update_envs]
    merged_env = []
    for orig_env in orig_envs:
        if orig_env not in update_names:
            merged_env.append(orig_env)
            continue
        for upd_env in update_envs:
            if orig_env.name == upd_env.name:
                merged_env.append(
                    models.ContainerEnvVar(
                        **{
                            **orig_env.model_dump(mode="python"),
                            **upd_env.model_dump(mode="python"),
                        }
                    )
                )
                break

    for upd_env in update_envs:
        if upd_env.name not in orig_names:
            merged_env.append(upd_env)
    return merged_env


def merge_io_channels(
    mounts: List[models.IOMount], volumes: List[models.IOVolume]
) -> List[models.IOChannel]:
    """
    Merge a list of IOMount objects and IOVolume objects to a list of IOChannel objects.

    Objects from IOMount are updated by objects from IOVolume with the same name.
    Objects from IOVolume with a name that does not occur in <mounts> are ignored.

    If two objects from both lists share the same name,
    overwrite values from the object in <mounts> with values from the object in <volumes>.
    """
    io_channels = []
    for mount in mounts:
        for vol in volumes:
            if mount.name == vol.name:
                io_channels.append(
                    models.IOChannel(
                        **{
                            **mount.model_dump(mode="python", exclude_none=True),
                            **vol.model_dump(mode="python", exclude_none=True),
                        }
                    )
                )
                break
    return io_channels


@functools.lru_cache()
def get_task_template(
    image: str,
    task_identifier: str,
    mode: str = "docker",
    registry_secret: str = None,
    namespace: str = None,
) -> models.TaskTemplate:
    kwargs = {}
    if registry_secret:
        kwargs["registry_secret"] = registry_secret
    if namespace:
        kwargs["namespace"] = namespace

    processing_container = get_processing_container(image=image, mode=mode, **kwargs)

    for template in processing_container.templates:
        if template.identifier == task_identifier:
            return template


@functools.lru_cache()
def get_processing_container(
    image: str,
    mode: str = "docker",
    namespace: str = "services",
    registry_secret: str = "registry-secret",
) -> models.ProcessingContainer:
    if mode == "k8s":
        from kaapana_containers.kubernetes.utils import KubernetsUtils

        with KubernetsUtils.extract_file_from_image(
            image,
            "/processing-container.json",
            namespace=namespace,
            registry_secret=registry_secret,
        ) as f:
            return models.ProcessingContainer(**json.load(f))
    elif mode == "docker":
        from kaapana_containers.docker.utils import DockerUtils

        with DockerUtils.extract_file_from_image(
            image, "/processing-container.json"
        ) as f:
            return models.ProcessingContainer(**json.load(f))
    else:
        raise ValueError(f"{mode=} must be one of ['docker','k8s']")
