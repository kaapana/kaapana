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
from kaapana.kubetools.pod_stopper import PodStopper

# NONE = None
# REMOVED = "removed"
# SCHEDULED = "scheduled"

# # set by the executor (t.b.d.)
# # LAUNCHED = "launched"

# # set by a task
# QUEUED = "queued"
# RUNNING = "running"
# SUCCESS = "success"
# SHUTDOWN = "shutdown"  # External request to shut down
# FAILED = "failed"
# UP_FOR_RETRY = "up_for_retry"
# UP_FOR_RESCHEDULE = "up_for_reschedule"
# UPSTREAM_FAILED = "upstream_failed"
# SKIPPED = "skipped"


# The scheduler processes tasks that have a state of NONE, SCHEDULED, QUEUED, and UP_FOR_RETRY.

# NONE is a newly created TaskInstance
# QUEUED is a task that is waiting for a slot in an executor and
# UP_FOR_RETRY means a task that failed before but needs to be retried.
# If the task has a state of NONE it will be set to SCHEDULED if the scheduler determines that it needs to run.
# Tasks in the SCHEDULED state are sent to the executor, at which point it is put into the QUEUED state until it actually runs.
# Unfortunately a race condition remains for UP_FOR_RETRY tasks as another scheduler can pick those up. To eliminate this the check for UP_FOR_RETRY needs to migrate from the TI to the scheduler. However, was it not for that fact that we have backfills... (see below)


class PodStatus(object):
    PENDING = 'pending'
    RUNNING = 'running'
    FAILED = 'failed'
    SUCCEEDED = 'succeeded'


class PodLauncher(LoggingMixin):
    pod_stopper = PodStopper()

    def __init__(self, kube_client=None, in_cluster=True, cluster_context=None,
                 extract_xcom=False):
        super(PodLauncher, self).__init__()
        self._client, self._batch_client, self._extensions_client = kube_client or get_kube_client(in_cluster=in_cluster,
                                                                                                   cluster_context=cluster_context)
        self._watch = watch.Watch()
        self.extract_xcom = extract_xcom

    def run_pod_async(self, pod):
        req = pod.get_kube_object()
        self.log.debug('Pod Creation Request: \n%s', json.dumps(req.to_dict(), indent=2))
        try:
            if pod.kind == "Pod":
                resp = self._client.create_namespaced_pod(body=req, namespace=pod.namespace)
            elif pod.kind == "Job":
                resp = self._batch_client.create_namespaced_job(body=req, namespace=pod.namespace)
            self.log.debug('Pod Creation Response: %s', resp)
        except ApiException:
            self.log.exception('Exception when attempting to create Namespaced Pod.')
            raise
        return resp

    def run_pod(self, pod, startup_timeout=360, heal_timeout=360, get_logs=True):
        # type: (Pod) -> (State, result)
        """
        Launches the pod synchronously and waits for completion.
        Args:
            pod (Pod):
            startup_timeout (int): Timeout for startup of the pod (if pod is pending for
             too long, considers task a failure
        """

        try:
            resp = self._client.read_namespaced_pod(name=pod.name,namespace=pod.namespace)
            self.log.debug('Pod already exists, we will delete it and then start your pod.')
            PodLauncher.pod_stopper.stop_pod_by_name(pod_id=resp.metadata.name)
        except ApiException as e:
            if e.status != 404:
                raise

        resp = self.run_pod_async(pod)
        curr_time = dt.now()

        last_status = None
        return_msg = None
        pull_time_reset = 0

        if resp.status.start_time is None:
            while self.pod_not_started(pod):
                if last_status != pod.last_kube_status:
                    pull_image = False
                    last_status = pod.last_kube_status
                    if pod.last_kube_status == "NONE" or pod.last_kube_status == None or pod.last_kube_status == "UNKNOWN":
                        self.log.error("Pod has status {} -> This is unexpected and treated as an fatal error!".format(pod.last_kube_status))
                        self.log.error("ABORT!")
                        exit(1)

                    elif pod.last_kube_status == "PENDING" or pod.last_kube_status == "ContainerCreating":
                        self.log.debug("Pod has status {} -> waiting...!".format(pod.last_kube_status))
                        pull_image = True

                    if pod.last_kube_status == "UNSCHEDULABLE":
                        self.log.warning("Pod has status {} -> Problems with POD-Quotas!".format(pod.last_kube_status))
                        self.log.warning("Pod should not have been scheduled...")
                        self.log.warning("-> waiting")

                    elif pod.last_kube_status == "ErrImagePull":
                        self.log.warning("Pod has status {} -> Problems with pulling the container image from the registry!".format(pod.last_kube_status))
                        self.log.warning("Image: {}".format(pod.image))
                        self.log.warning("-> waiting")

                    elif pod.last_kube_status == "FAILED":
                        self.log.error("Pod has status {} -> Something went wrong within the container!".format(pod.last_kube_status))

                    elif pod.last_kube_status == "RUNNING":
                        self.log.debug("Pod has status {} -> container still running.".format(pod.last_kube_status))


                delta = dt.now() - curr_time
                if delta.seconds >= startup_timeout and pull_image and pull_time_reset <= 3:
                    pull_time_reset += 1
                    self.log.warning("Pod is still downloading the container! -> reset startup-timeout! counter: {}".format(pull_time_reset))
                    curr_time = dt.now()
                    continue

                if delta.seconds >= startup_timeout:
                    self.log.exception('Pod took too long to start! startup_timeout: {}'.format(startup_timeout))
                    return_msg = ("No message", pod.last_kube_status)
                    break
                    # raise AirflowException("Pod took too long to start")

                time.sleep(1)

        if return_msg is None:
            return_msg = self._monitor_pod(pod, get_logs)
            print("RETURN MESSAGE:")
            print(return_msg)

        return return_msg

    def _monitor_pod(self, pod, get_logs):
        # type: (Pod) -> (State, content)
        try:
            if get_logs:
                _pod = self.read_pod(pod)
                logs = self._client.read_namespaced_pod_log(
                    name=_pod.metadata.name,
                    namespace=_pod.metadata.namespace,
                    container=_pod.spec.containers[0].name,
                    follow=True,
                    tail_lines=10,
                    _preload_content=False)
                for log in logs:
                    self.log.info(log)
                    # log = log.decode("utf-8").replace("\n","").split("\\n")
                    # for line in log:
                    # self.log.info(line)

            result = None
            if self.extract_xcom:
                while self.base_container_is_running(pod):
                    self.log.info('Container %s has state %s', pod.name, State.RUNNING)
                    time.sleep(2)
                result = self._extract_xcom(pod)
                self.log.info(result)
                result = json.loads(result)
            while self.pod_is_running(pod):
                self.log.debug('Pod %s has state %s', pod.name, State.RUNNING)
                time.sleep(2)
            return (self._task_status(pod=pod, event=self.read_pod(pod)), result)
        except Exception as e:
            self.log.warn(f"################# ISSUE! Could not _monitor_pod: {pod.metadata.name}")
            self.log.warn(f"################# ISSUE! message: {e}")

    def _task_status(self, pod, event):
        af_status, kube_status = self.process_status(event=event, pod=pod)
        if kube_status != pod.last_kube_status:
            self.log.info('############## Container: %s had an event of type %s', event.metadata.name, kube_status)
        pod.last_kube_status = kube_status
        pod.last_af_status = af_status
        return af_status

    def pod_not_started(self, pod):
        state = self._task_status(pod=pod, event=self.read_pod(pod))
        return state == State.QUEUED or state == State.SCHEDULED

    def pod_is_running(self, pod):
        state = self._task_status(pod=pod, event=self.read_pod(pod))
        return state == State.RUNNING

    def base_container_is_running(self, pod):
        event = self.read_pod(pod)
        status = next(iter(filter(lambda s: s.name == 'base', event.status.container_statuses)), None)
        return status.state.running is not None

    def read_pod(self, pod):
        try:
            if pod.kind == "Pod":
                return self._client.read_namespaced_pod(pod.name, pod.namespace)
            elif pod.kind == "Job":
                job_name = self._batch_client.read_namespaced_job(pod.name, pod.namespace).metadata._name
                pod_list = self._client.list_namespaced_pod(namespace=pod.namespace)
                for pod_running in pod_list.items:
                    if "job-name" in pod_running.metadata._labels and pod_running.metadata._labels['job-name'] == job_name:
                        return pod_running
            return self._client.read_namespaced_pod(pod.name, pod.namespace)

        except HTTPError as e:
            raise AirflowException(f'There was an error reading the kubernetes API: {e}')

    def _extract_xcom(self, pod):
        resp = kubernetes_stream(self._client.connect_get_namespaced_pod_exec,
                                 pod.name, pod.namespace,
                                 container=self.kube_req_factory.SIDECAR_CONTAINER_NAME,
                                 command=['/bin/sh'], stdin=True, stdout=True,
                                 stderr=True, tty=False,
                                 _preload_content=False)
        try:
            result = self._exec_pod_command(
                resp, 'cat {}/return.json'.format(self.kube_req_factory.XCOM_MOUNT_PATH))
            self._exec_pod_command(resp, 'kill -s SIGINT 1')
        finally:
            resp.close()
        if result is None:
            raise AirflowException('Failed to extract xcom from pod: {}'.format(pod.name))
        return result

    def _exec_pod_command(self, resp, command):
        if resp.is_open():
            self.log.info('Running command... %s\n' % command)
            resp.write_stdin(command + '\n')
            while resp.is_open():
                resp.update(timeout=1)
                if resp.peek_stdout():
                    return resp.read_stdout()
                if resp.peek_stderr():
                    self.log.info(resp.read_stderr())
                    break

    def process_status(self, event, pod):
        af_status = "None"
        kube_status = "None"
        if event.status.container_statuses is not None:
            for container_state in event.status.container_statuses:
                container_name = container_state.name
                container_image = container_state.image
                container_ready = container_state.ready
                container_restart_count = container_state.restart_count
                state_running = container_state.state.running
                state_terminated = container_state.state.terminated
                state_waiting = container_state.state.waiting

                if state_terminated is not None:
                    container_id = state_terminated.container_id
                    exit_code = state_terminated.exit_code
                    message = state_terminated.message
                    reason = state_terminated.reason
                    signal = state_terminated.signal
                    if exit_code != 0:
                        self.log.warn("")
                        self.log.warn("######## Container Error !!")
                        self.log.warn("")

                        af_status = State.FAILED
                        kube_status = "FAILED"

                    else:
                        self.log.info("Container finished successfully.")
                        af_status = State.SUCCESS
                        kube_status = "SUCCESS"

                elif state_waiting is not None:
                    if state_waiting.reason == 'ErrImagePull' or state_waiting.reason == 'ImagePullBackOff':
                        af_status = State.QUEUED
                        kube_status = "ErrImagePull"

                    elif state_waiting.reason == 'ContainerCreating':
                        kube_status = "ContainerCreating"
                        af_status = State.QUEUED

                    else:
                        self.log.info("#################### Container not running - reason: {}".format(state_waiting.reason))

                elif state_running is not None:
                    af_status = State.RUNNING
                    kube_status = "RUNNING"

                else:
                    self.log.warning("")
                    self.log.warning("######## Container unknown state !!")
                    self.log.warning(event.status)
                    self.log.warning("")
                    self.log.warning("Container_state: ")
                    self.log.warning("container_name: {}".format(container_name))
                    self.log.warning("container_image: {}".format(container_image))
                    self.log.warning("container_ready: {}".format(container_ready))
                    self.log.warning("container_restart_count: {}".format(container_restart_count))
                    self.log.warning("state_running: {}".format(state_running))
                    self.log.warning("state_terminated: {}".format(state_terminated))
                    self.log.warning("state_waiting: {}".format(state_waiting))
                    af_status = State.FAILED
                    kube_status = "UNKNOWN"

        elif event.status.phase == "Pending":
            if event.status.conditions != None and len(event.status.conditions) != 0 and event.status.conditions[0].reason == "Unschedulable":
                if pod.last_kube_status != "UNSCHEDULABLE":
                    self.log.warning("Insufficient quota: {}".format(event.status.conditions[0].message))
                af_status = State.SCHEDULED
                kube_status = "UNSCHEDULABLE"
            else:
                af_status = State.QUEUED
                kube_status = "PENDING"

        else:
            self.log.info("No container status available yet.")
            self.log.info(event.status)
            af_status = State.QUEUED
            kube_status = "NONE"

        return af_status, kube_status
