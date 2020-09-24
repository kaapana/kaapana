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
import json

class ServiceFinder(LoggingMixin):
    def __init__(self, kube_client=None, in_cluster=True, cluster_context=None,
                 extract_xcom=False):
        super(ServiceFinder, self).__init__()
        self._client,self._batch_client,self._extensions_client = kube_client or get_kube_client(in_cluster=in_cluster,
                                                      cluster_context=cluster_context)

    def find_service(self, namespace):
        self.log.debug('Service Find Request Created')
        try: 
            resp = self._client.list_namespaced_service(namespace=namespace, pretty=True)
            self.log.debug('Service Find Response: %s', resp)
        except ApiException:
            self.log.exception('Exception when attempting to find namespaced Service.')
            raise
        return resp