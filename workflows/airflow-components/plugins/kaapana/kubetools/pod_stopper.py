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

from airflow.utils.log.logging_mixin import LoggingMixin
from kubernetes.client.rest import ApiException
from kubernetes import client
from airflow import AirflowException
from kaapana.kubetools.kube_client import get_kube_client
import json


class PodStopper(LoggingMixin):
    def __init__(self, kube_client=None, in_cluster=True, cluster_context=None):
        super(PodStopper, self).__init__()
        self._client, self._batch_client, self._extensions_client = kube_client or get_kube_client(in_cluster=in_cluster,
                                                                                                   cluster_context=cluster_context)

    def stop_pod(self, pod):
        req = client.V1DeleteOptions()
        try:
            if pod.kind == "Pod":
                resp = self._client.delete_namespaced_pod(
                    name=pod.metadata.name, body=req, namespace=pod.metadata.namespace, grace_period_seconds=0, pretty=True)
                # self.log.info('Pod Deletion Response: %s', resp)
                return resp
        except ApiException:
            self.log.exception(
                'Exception when attempting to delete namespaced Pod.')
            raise

    def stop_pod_by_name(self, pod_id, namespace="flow-jobs"):
        req = client.V1DeleteOptions()
        try:
            self.log.info("In 'stop_pod_by_name'")
            self.log.info("Delete Pod: {}".format(pod_id))
            self.log.info("Namespace: {}".format(namespace))
            resp = self._client.delete_namespaced_pod(name=pod_id, body=req, namespace=namespace, grace_period_seconds=0, pretty=True)
            return resp
        except ApiException:
            self.log.exception('Exception when attempting to delete namespaced Pod.')
            self.log.warn("Could not delete pod: {}".format(pod_id))
            # raise
