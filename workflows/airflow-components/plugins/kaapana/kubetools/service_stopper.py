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
from airflow import AirflowException
from kaapana.kubetools.kube_client import get_kube_client
from kubernetes import client
import json

class ServiceStopper(LoggingMixin):
    def __init__(self, kube_client=None, in_cluster=True, cluster_context=None):
        super(ServiceStopper, self).__init__()
        self._client, self._batch_client, self._extensions_client = kube_client or get_kube_client(in_cluster=in_cluster,
                                                                                                   cluster_context=cluster_context)

    def stop_service(self, service):
        req = client.V1DeleteOptions()
        self.log.info('Service Deletion Request: \n%s',
                       json.dumps(req.to_dict(), indent=2))
        try:
            if service.kind == "Service":
                resp = self._client.delete_namespaced_service(
                    name=service.metadata.name, body=req, namespace=service.metadata.namespace, pretty=True)
                self.log.info('Service Deletion Response: %s', resp)
                return resp
        except ApiException:
            self.log.exception(
                'Exception when attempting to delete namespaced Service.')
            raise
