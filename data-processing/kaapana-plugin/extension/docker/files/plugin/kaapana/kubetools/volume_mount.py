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


class VolumeMount:
    """Defines Kubernetes Volume Mount"""

    def __init__(self, name, mount_path, sub_path, read_only, mount_propagation=None):
        """Initialize a Kubernetes Volume Mount. Used to mount pod level volumes to
        running container.
        :param name: the name of the volume mount
        :type name: str
        :param mount_path:
        :type mount_path: str
        :param sub_path: subpath within the volume mount
        :type sub_path: str
        :param read_only: whether to access pod with read-only mode
        :type read_only: bool
        :param mount_propagation: Kubernetes Mount propagation: https://kubernetes.io/docs/concepts/storage/volumes/#mount-propagation
        :type read_only: str
        """
        self.name = name
        self.mount_path = mount_path
        self.sub_path = sub_path
        self.read_only = read_only
        self.mount_propagation = mount_propagation

    def get_kube_object(self):
        kube_volume_mount = kubernetes.client.V1VolumeMount(
            mount_path=self.mount_path, name=self.name
        )

        kube_volume_mount.sub_path = self.sub_path
        kube_volume_mount.read_only = self.read_only
        kube_volume_mount.mount_propagation = self.mount_propagation

        return kube_volume_mount
