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
from kaapana.kubetools.kube_client import get_kube_client
from kaapana.blueprints.kaapana_global_variables import JOBS_NAMESPACE
import time


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

    def stop_pod_by_name(self, pod_id, namespace=JOBS_NAMESPACE, phases=None):
        max_tries= 20
        delay=6
        tries = 0 
        found = False 
        req = client.V1DeleteOptions()
        print("")
        self.log.info(f"################ Deleting Pod: {pod_id}")
        try:
            while tries < max_tries:
                self.log.info(f"### attempt: {tries}")
                try:
                    resp = self._client.read_namespaced_pod(name=pod_id,namespace=namespace)
                    found = True
                    if phases is not None and resp.status.phase not in phases:
                        success_message = f"################ Skipping deleting, since its not in phase {','.join(phases)}!"
                        break
                    self._client.delete_namespaced_pod(name=pod_id, body=req, namespace=namespace, grace_period_seconds=0) 
                except ApiException as e:
                    if e.status != 404:
                        raise
                    else:
                        success_message = "################ Pod deleted."
                        break
                time.sleep(delay+tries)
                tries+=1
            
            if tries >= max_tries:
                self.log.info("################ Could not delete pod!")
            elif not found:
                self.log.info("################ Pod not found!")
            else:
                self.log.info(success_message)

            print("")

        except Exception as e:
            self.log.exception("Exception when attempting to delete namespaced Pod.")
            self.log.exception(f"Could not delete pod: {pod_id}")
            self.log.exception(e)

