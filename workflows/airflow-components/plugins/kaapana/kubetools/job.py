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


class Job():
    """
    Represents a kubernetes Job and manages execution of a single Job.
    :param image: The docker image
    :type image: str
    :param envs: A dict containing the environment variables
    :type envs: dict
    :param cmds: The command to be run on the Job
    :type cmds: list str
    :param secrets: Secrets to be launched to the Job
    :type secrets: list Secret
    :param result: The result that will be returned to the operator after
                   successful execution of the Job
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
            args=None,
            api_version='batch/v1',
            kind='Job',
            secrets=None,
            labels=None,
            node_selectors=None,
            name=None,
            volumes=None,
            volume_mounts=None,
            namespace='default',
            result=None,
            image_pull_policy='IfNotPresent',
            image_pull_secrets=None,
            init_containers=None,
            service_account_name=None,
            resources=None,
            annotations=None,
            restart_policy='Never',
            active_deadline_seconds=None,
            backoff_limit=None,
            completions=None,
            manual_selector=None,
            parallelism=None,
            affinity=None
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
        self.name = name + str(uuid.uuid1())[:8]
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
        self.active_deadline_seconds = active_deadline_seconds
        self.backoff_limit = backoff_limit
        self.completions = completions
        self.manual_selector = manual_selector
        self.parallelism = parallelism

    def get_kube_object(self):
        kube_job = kubernetes.client.V1Job()
        kube_job.api_version = self.api_version
        kube_job.kind = self.kind

        # metadata
        job_metadata = kubernetes.client.V1ObjectMeta()
        job_metadata.name = self.name
        job_metadata.namespace = self.namespace
        job_metadata.labels = self.labels
        kube_job.metadata = job_metadata

        # spec
        job_spec = kubernetes.client.V1JobSpec(
            template=kubernetes.client.V1PodTemplateSpec())
        job_spec.active_deadline_seconds = self.active_deadline_seconds
        job_spec.backoff_limit = self.backoff_limit
        job_spec.completions = self.completions
        job_spec.manual_selector = self.manual_selector
        job_spec.parallelism = self.parallelism

        # spec - template
        template = kubernetes.client.V1PodTemplateSpec()

        # spec - template - metadata
        job_template_metadata = kubernetes.client.V1ObjectMeta()
        job_template_metadata.name = self.name
        job_template_metadata.namespace = self.namespace
        job_template_metadata.labels = self.labels
        template.metadata = job_template_metadata

        # spec - template - spec

        job_template_spec = kubernetes.client.V1PodSpec(containers=[])
        job_template_spec.restart_policy = self.restart_policy

        # spec - template - spec - container
        job_container = kubernetes.client.V1Container(
            name=self.name+"-container")
        job_container.command = self.cmds
        job_container.args = self.args

        job_container.env = self.get_envs()
        job_container.image = self.image
        job_container.image_pull_policy = self.image_pull_policy

        job_container.resources = self.resources.get_kube_object()
        job_container.volume_mounts = []

        # spec - template - spec - container - volume_mounts
        for volume_mount in self.volume_mounts:
            job_container.volume_mounts.append(volume_mount.get_kube_object())

        for secret in self.secrets:
            job_container.volume_mounts.append(
                secret.get_kube_object_volume_mount())

        job_template_spec.containers.append(job_container)

        # spec - template - spec - image_pull_secrets
        job_template_spec.image_pull_secrets = []
        for ip_secret_name in self.image_pull_secrets:
            ip_secret = kubernetes.client.V1LocalObjectReference()
            ip_secret.name = ip_secret_name
            job_template_spec.image_pull_secrets.append(ip_secret)

        # spec - template - spec - volumes
        job_template_spec.volumes = []
        for volume in self.volumes:
            job_template_spec.volumes.append(volume.get_kube_object())

        for secret in self.secrets:
            job_template_spec.volumes.append(secret.get_kube_object_volume())

        template.spec = job_template_spec

        job_spec.template = template

        kube_job.spec = job_spec

        return kube_job

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
