# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import kubernetes
from kaapana.kubetools.resources import Resources
import uuid


class Pod:
    """
    Represents a kubernetes pod and manages execution of a single pod.
    :param image: The docker image
    :type image: str
    :param envs: A dict containing the environment variables
    :type envs: dict
    :param cmds: The command to be run on the pod
    :type cmds: list str
    :param secrets: Secrets to be launched to the pod
    :type secrets: list Secret
    :param result: The result that will be returned to the operator after
                   successful execution of the pod
    :type result: any
    :param image_pull_policy: Specify a policy to cache or always pull an image
    :type image_pull_policy: str
    :param restart_policy: PodSpec restartPolicy field with possible values Always, OnFailure, and Never - default='Never'
    :type restart_policy: str
    :param affinity: A dict containing a group of affinity scheduling rules
    :type affinity: dict
    """

    def __init__(
        self,
        image,
        envs,
        cmds,
        app_name=None,
        args=None,
        api_version="v1",
        kind="Pod",
        secrets=None,
        labels=None,
        node_selectors=None,
        name=None,
        volumes=None,
        volume_mounts=None,
        namespace="default",
        result=None,
        image_pull_policy="IfNotPresent",
        image_pull_secrets=None,
        init_containers=None,
        service_account_name=None,
        resources=None,
        annotations=None,
        restart_policy="Never",
        affinity=None,
    ):
        self.image = image
        self.envs = envs or {}
        self.cmds = cmds
        self.args = args or []
        self.api_version = api_version
        self.kind = kind
        self.secrets = secrets or []
        self.result = result
        self.labels = labels or {}
        self.name = name
        self.volumes = volumes or []
        self.volume_mounts = volume_mounts or []
        self.node_selectors = node_selectors or []
        self.namespace = namespace
        self.image_pull_policy = image_pull_policy
        self.image_pull_secrets = image_pull_secrets
        self.init_containers = init_containers
        self.service_account_name = service_account_name
        self.resources = resources or Resources()
        self.annotations = annotations or {}
        self.restart_policy = restart_policy
        self.affinity = affinity or {}
        self.last_kube_status = None
        self.last_af_status = None
        self.task_instance = None

    def get_kube_object(self):
        pod_api_version = self.api_version
        pod_kind = self.kind

        # metadata
        pod_metadata = kubernetes.client.V1ObjectMeta()
        pod_metadata.name = self.name
        pod_metadata.namespace = self.namespace
        pod_metadata.labels = self.labels

        # spec
        pod_spec = kubernetes.client.V1PodSpec(containers=[])
        pod_spec.restart_policy = self.restart_policy

        # spec - node_selector
        if self.node_selectors is not None and len(self.node_selectors) is not 0:
            pod_spec.node_selector = self.node_selectors

        # spec - init_container
        if self.init_containers is not None:
            config = self.init_containers
            pod_spec.init_containers = []
            pod_init_container = kubernetes.client.V1Container(
                name=self.name + "-init-container"
            )
            if "cmds" in config:
                pod_init_container.command = config["cmds"]
            if "args" in config:
                pod_init_container.args = config["args"]

            if "env" in config:
                pod_init_container.env = config["env"]
            if "image" in config:
                pod_init_container.image = config["image"]
            if "image_pull_policy" in config:
                pod_init_container.image_pull_policy = config["image_pull_policy"]

            pod_init_container.volume_mounts = []

            # spec - init_container - volume_mounts
            for volume_mount in self.volume_mounts:
                pod_init_container.volume_mounts.append(volume_mount.get_kube_object())

            pod_spec.init_containers.append(pod_init_container)

        # spec - container
        pod_spec.containers = []
        pod_container = kubernetes.client.V1Container(name=self.name)
        pod_container.command = self.cmds
        pod_container.args = self.args

        pod_container.env = self.get_envs()
        pod_container.image = self.image
        pod_container.image_pull_policy = self.image_pull_policy

        pod_container.resources = self.resources.get_kube_object()
        pod_container.volume_mounts = []

        # spec - container - volume_mounts
        for volume_mount in self.volume_mounts:
            pod_container.volume_mounts.append(volume_mount.get_kube_object())

        for secret in self.secrets:
            pod_container.volume_mounts.append(secret.get_kube_object_volume_mount())

        pod_spec.containers.append(pod_container)

        # spec - image_pull_secrets
        pod_spec.image_pull_secrets = []
        for ip_secret_name in self.image_pull_secrets:
            ip_secret = kubernetes.client.V1LocalObjectReference()
            ip_secret.name = ip_secret_name
            pod_spec.image_pull_secrets.append(ip_secret)

        # spec - volumes
        pod_spec.volumes = []
        for volume in self.volumes:
            pod_spec.volumes.append(volume.get_kube_object())

        for secret in self.secrets:
            pod_spec.volumes.append(secret.get_kube_object_volume())

        pod_status = kubernetes.client.V1PodStatus()

        kube_pod = kubernetes.client.V1Pod(
            api_version=pod_api_version,
            kind=pod_kind,
            metadata=pod_metadata,
            spec=pod_spec,
            status=pod_status,
        )

        return kube_pod

    def get_envs(self):
        container_envs = []
        for env_key in self.envs.keys():
            env = kubernetes.client.V1EnvVar(name=env_key)
            env.value = self.envs[env_key]

            # if "value" in env_config:
            # env.value = env_config["value"]

            # if "valueFrom" in env_config:
            #     env_value_from = kubernetes.client.V1EnvVarSource()

            #     if "configMapKeyRef" in env_config:
            #         config = env_config["configMapKeyRef"]
            #         configMapKeySelector = kubernetes.client.V1ConfigMapKeySelector()
            #         if "name" in config:
            #             configMapKeySelector.name = config["name"]
            #         if "key" in config:
            #             configMapKeySelector.key = config["key"]
            #         if "optional" in config:
            #             configMapKeySelector.optional = config["optional"]
            #         env_value_from.config_map_key_ref = configMapKeySelector

            #     elif "fieldRef" in env_config:
            #         config = env_config["fieldRef"]
            #         objectFieldSelector = kubernetes.client.V1ObjectFieldSelector()
            #         if "api_version" in config:
            #             objectFieldSelector.api_version = config["api_version"]
            #         if "field_path" in config:
            #             objectFieldSelector.field_path = config["field_path"]

            #         env_value_from.field_ref = objectFieldSelector

            #     elif "resourceFieldRef" in env_config:
            #         config = env_config["resourceFieldRef"]
            #         resourceFieldSelector = kubernetes.client.V1ResourceFieldSelector()
            #         if "container_name" in config:
            #             resourceFieldSelector.container_name = config["container_name"]
            #         if "divisor" in config:
            #             resourceFieldSelector.divisor = config["containdivisorer_name"]
            #         if "resource" in config:
            #             resourceFieldSelector.resource = config["resource"]
            #         env_value_from.resource_field_ref = resourceFieldSelector

            #     elif "secretKeyRef" in env_config:
            #         config = env_config["secretKeyRef"]
            #         secretKeySelector = kubernetes.client.V1SecretKeySelector()

            #         if "name" in config:
            #             secretKeySelector.name = config["name"]
            #         if "key" in config:
            #             secretKeySelector.key = config["key"]
            #         if "optional" in config:
            #             secretKeySelector.optional = config["optional"]
            #         env_value_from.secret_key_ref = secretKeySelector

            # env.value_from = env_value_from
            container_envs.append(env)

        for secret in self.secrets:
            container_envs.append(secret.get_kube_object_env())

        return container_envs
