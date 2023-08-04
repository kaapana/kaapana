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
import os


class Secret:
    """Defines Kubernetes Secret Volume"""

    def __init__(self, deploy_type, deploy_target, secret, key, optional=False):
        """Initialize a Kubernetes Secret Object. Used to track requested secrets from
        the user.
        :param deploy_type: The type of secret deploy in Kubernetes, either `env` or
            `volume`
        :type deploy_type: ``str``
        :param deploy_target: The environment variable when `deploy_type` `env` or
            file path when `deploy_type` `volume` where expose secret
        :type deploy_target: ``str``
        :param secret: Name of the secrets object in Kubernetes
        :type secret: ``str``
        :param key: Key of the secret within the Kubernetes Secret
        :type key: ``str``
        :param optional: Specify whether the Secret or it's key must be defined
        :type optional: ``boolean``
        """
        self.deploy_type = deploy_type
        self.deploy_target = deploy_target
        if deploy_type == "env":
            self.deploy_target = deploy_target.upper()
        self.secret = secret
        self.key = key
        self.optional = optional

    def get_kube_object_env(self):
        if self.deploy_type == "env":
            env = kubernetes.client.V1EnvVar()
            env.name = self.deploy_target

            env_value_from = kubernetes.client.V1EnvVarSource()

            secretKeySelector = kubernetes.client.V1SecretKeySelector()
            secretKeySelector.name = self.secret
            secretKeySelector.key = self.key
            secretKeySelector.optional = self.optional

            env_value_from.secret_key_ref = secretKeySelector
            env.value_from = env_value_from

            return env

        else:
            return None

    def get_kube_object_volume(self):
        if self.deploy_type == "volume":
            kube_volume = kubernetes.client.V1Volume()
            kube_volume.name = self.secret + "_volume"
            secretVolumeSource = kubernetes.client.V1SecretVolumeSource()
            secretVolumeSource.optional = self.optional
            secretVolumeSource.secret_name = self.secret

            secretVolumeSource.items = []
            item = kubernetes.client.V1KeyToPath()
            item.key = self.key
            item.path = os.path.basename(self.deploy_target)
            secretVolumeSource.items.append(item)

            kube_volume.secret = secretVolumeSource

            return kube_volume

    def get_kube_object_volume_mount(self):
        if self.deploy_type == "volume":
            kube_volume_mount = kubernetes.client.V1VolumeMount()

            kube_volume_mount.name = self.secret + "_volume"
            kube_volume_mount.mount_path = self.deploy_target
            kube_volume_mount.sub_path = os.path.basename(self.deploy_target)
            kube_volume_mount.read_only = True

            return kube_volume_mount
        else:
            return None
