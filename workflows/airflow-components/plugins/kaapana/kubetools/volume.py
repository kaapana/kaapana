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


class Volume:
    """Defines Kubernetes Volume"""

    def __init__(self, name, configs):
        """ Adds Kubernetes Volume to pod. allows pod to access features like ConfigMaps
        and Persistent Volumes
        :param name: the name of the volume mount
        :type: name: str
        :param configs: dictionary of any features needed for volume.
        We purposely keep this vague since there are multiple volume types with changing
        configs.
        :type: configs: dict
        """
        self.name = name
        self.configs = configs

    def get_kube_object(self):
        kube_volume = kubernetes.client.V1Volume(name=self.name)
        kube_volume.name = self.name

        if "PersistentVolumeClaim" in self.configs:
            config = self.configs["PersistentVolumeClaim"]

            kube_volume_pvc = kubernetes.client.V1PersistentVolumeClaimVolumeSource(claim_name=config["claim_name"])
            kube_volume_pvc.claim_name = config["claim_name"]
            kube_volume_pvc.read_only = config["read_only"]
            kube_volume.persistent_volume_claim = kube_volume

        elif "GitRepo" in self.configs:
            config = self.configs["GitRepo"]

            kube_volume_git = kubernetes.client.V1GitRepoVolumeSource()
            kube_volume_git.directory = config["directory"]
            kube_volume_git.repository = config["repository"]
            kube_volume_git.revision = config["revision"]
            kube_volume.git_repo = kube_volume_git

        elif "configMap" in self.configs:
            config = self.configs["configMap"]

            kube_volume_cm = kubernetes.client.V1ConfigMapVolumeSource()
            kube_volume_cm.name = config["name"]
            kube_volume_cm.default_mode = config["default_mode"]
            kube_volume_cm.optional = config["optional"]

            items = []
            for key_config in config["keys"]:
                kube_volume_cm_key = kubernetes.client.V1KeyToPath()
                kube_volume_cm_key.key = key_config["key"]
                kube_volume_cm_key.mode = key_config["mode"]
                kube_volume_cm_key.path = key_config["path"]
                items.append(kube_volume_cm_key)

                kube_volume_cm.items = items

            kube_volume.config_map = kube_volume_cm

        elif "emptyDir" in self.configs:
            config = self.configs["emptyDir"]

            kube_volume_ed = kubernetes.client.V1EmptyDirVolumeSource()
            if "medium" in config:
                kube_volume_ed.medium = config["medium"]
            if "size_limit" in config:
                kube_volume_ed.size_limit = config["size_limit"]
            kube_volume.empty_dir = kube_volume_ed

        elif "hostPath" in self.configs:
            config = self.configs['hostPath']

            kube_volume_hp = kubernetes.client.V1HostPathVolumeSource(path=config["path"])
            if "type" in config:
                kube_volume_hp.type = config["type"]

            kube_volume.host_path = kube_volume_hp

        elif "secret" in self.configs:
            config = self.configs['secret']
            secretVolumeSource = kubernetes.client.V1SecretVolumeSource()
            if "default_mode" in config:
                secretVolumeSource.default_mode = config["default_mode"]
            if "optional" in config:
                secretVolumeSource.optional = config["optional"]
            if "secret_name" in config:
                secretVolumeSource.secret_name = config["secret_name"]

            if "items" in config:
                secretVolumeSource.items = []
                for item_config in config["items"]:
                    item = kubernetes.client.V1KeyToPath()
                    if "key" in item_config:
                        item.key = item_config["key"]
                    if "mode" in item_config:
                        item.mode = item_config["mode"]
                    if "path" in item_config:
                        item.path = item_config["path"]
                    secretVolumeSource.items.append(item)

            kube_volume.secret = secretVolumeSource

        return kube_volume
