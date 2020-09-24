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

import json
import time
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.state import State
from datetime import datetime as dt
from kubernetes import watch
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream as kubernetes_stream
from airflow import AirflowException
from requests.exceptions import HTTPError
from kaapana.kubetools.kube_client import get_kube_client


class ServiceStatus(object):
    PENDING = 'pending'
    RUNNING = 'running'
    FAILED = 'failed'
    SUCCEEDED = 'succeeded'


class ServiceLauncher(LoggingMixin):
    def __init__(self, kube_client=None, in_cluster=True, cluster_context=None,
                 extract_xcom=False):
        super(ServiceLauncher, self).__init__()
        self._client,self._batch_client,self._extensions_client = kube_client or get_kube_client(in_cluster=in_cluster,
                                                      cluster_context=cluster_context)
        self._watch = watch.Watch()
        self.extract_xcom = extract_xcom

    def run_service_async(self, service):
        req = service.get_kube_object()
        self.log.debug('Service Creation Request: \n%s', json.dumps(req.to_dict(), indent=2))
        try:
            if service.kind == "Service":
                resp = self._client.create_namespaced_service(body=req, namespace=service.namespace, pretty=True)
                self.log.info(resp)
            self.log.debug('Service Creation Response: %s', resp)
        except ApiException:
            self.log.exception('Exception when attempting to create namespaced Service.')
            raise
        return resp

    def run_service(self, service, startup_timeout=120, get_logs=True):
        """
        Launches the service synchronously and waits for completion.
        Args:
            service (Service):
            startup_timeout (int): Timeout for startup of the service (if service is pending for
             too long, considers task a failure
        """
        resp = self.run_service_async(service)
        return self._monitor_service(service, get_logs)

    def _monitor_service(self, service, get_logs):

        if get_logs:
            _service=self.read_service(service)
            logs = self._client.read_namespaced_service(
                name=_service.metadata.name,
                namespace=_service.metadata.namespace, pretty=True)
            self.log.info(logs)
        result = None
        return

    def read_service(self, service):
        try:
            if service.kind == "Service":
                return self._client.read_namespaced_service(service.name, service.namespace)

        except HTTPError as e:
            raise AirflowException(
                'There was an error reading the kubernetes API: {}'.format(e)
            )