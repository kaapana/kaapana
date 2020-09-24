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

class Resources:
    def __init__(
            self,
            request_memory=None,
            request_cpu=None,
            limit_memory=None,
            limit_cpu=None,
            limit_gpu=None):
        self.request_memory = request_memory
        self.request_cpu = request_cpu
        self.limit_memory = limit_memory
        self.limit_cpu = limit_cpu
        self.limit_gpu = limit_gpu

    def is_empty_resource_request(self):
        return not self.has_limits() and not self.has_requests()

    def has_limits(self):
        return self.limit_cpu is not None or self.limit_memory is not None or self.limit_gpu is not None

    def has_requests(self):
        return self.request_cpu is not None or self.request_memory is not None

    def get_kube_object(self):
        kube_resources = kubernetes.client.V1ResourceRequirements()
        if self.has_requests():
            requests = {}

            if self.request_cpu is not None:
                requests['cpu'] = self.request_cpu
            if self.request_memory is not None:
                requests['memory'] = self.request_memory
            kube_resources.requests = requests

        if self.has_limits():
            limits = {}

            if self.limit_cpu is not None:
                limits['cpu'] = self.limit_cpu
            if self.limit_memory is not None:
                limits['memory'] = self.limit_memory
            if self.limit_gpu is not None:
                limits['nvidia.com/gpu'] = self.limit_gpu
            kube_resources.limits = limits

        return kube_resources
