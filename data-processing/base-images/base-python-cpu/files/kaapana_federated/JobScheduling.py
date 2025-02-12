import logging
import time
from collections import deque

from kaapana_federated.Exceptions import (
    FederatedJobFaildException,
    FederatedJobTimeoutException,
)
from kaapana_federated.KaapanaFedServices import KaapanaFedWorkflowService, KaapanaJob


class RemoteJobScheduler:
    """
    This class distributes jobs accross remote instances, keeps track of their execution history and enables waiting till all remote jobs are finished.
    Parallel job scheduling is note implemeted jet, creating a new job an an instance will "overwrite" the old one (e.g. only the latest job is awaited)
    A history of jobs per site is available
    """

    def __init__(
        self,
        instance_names: list[str],
        client: KaapanaFedWorkflowService,
        history_length: int = 3,
        wait_timeout_seconds: int = 10000,
    ):
        """
        history_length denotes the length of previous encqued jobs
        """
        self.log = logging.getLogger(__name__)
        self.log.info("Remote Instance Names:", instance_names)
        self.client = client
        self.instances = {
            instance.instance_name: instance
            for instance in self.client.getInstances(instance_names=instance_names)
        }

        # Init job history with nones
        self.history_length = history_length
        template = deque(maxlen=history_length)
        for i in range(0, self.history_length):
            template.append(None)

        self.jobOnInstance = {
            instance.instance_name: template.copy()
            for instance in self.client.getInstances(instance_names=instance_names)
        }

        self.wait_timeout_seconds = wait_timeout_seconds

    @property
    def instance_names(self):
        return self.instances.keys()

    def create_job(
        self,
        instance_name: str,
        dag_id: str,
        conf_data: dict,
        usernaem: str,
        workflow_id: str,
    ):
        jobs = self.client.createJob(
            dag_id=dag_id,
            conf_data=conf_data,
            username=usernaem,
            instance_name=instance_name,
            workflow_id=workflow_id,
        )

        self.log.info(
            "Created Jobs on local backend and added to orchestrating workflow",
            jobs,
        )

        self.jobOnInstance[instance_name].appendleft(jobs[0])

    def get_job(self, instance_name: str, history_index: int = 0) -> KaapanaJob:
        if history_index >= self.history_length or history_index < 0:
            raise ValueError(
                "Requested index is out of bounds for job history", index=history_index
            )
        return self.jobOnInstance[instance_name][history_index]

    def wait_for_jobs(self):
        """
        This method blocks until all currently created jobs are completed
        """
        updated = {instance_name: False for instance_name in self.instance_names}

        self.log.info("Wait for Updates")

        for second in range(self.wait_timeout_seconds):
            time.sleep(1)

            # every 60 seconds
            if second % 60 == 0:
                self.log.info("Waited for %d seconds")
                self.log.debug("Status: %s", str(updated))

            # every 10 seconds
            if second % 10 == 0:
                for instance_name in self.instance_name:
                    job = self.get_job(instance_name)
                    if job.isFaild:
                        raise FederatedJobFaildException(
                            instance_name=instance_name, job_id=job.id
                        )
                    updated[instance_name] = job.isFinished

                if all(updated.values()):
                    break

        if not all(updated.values()):
            raise FederatedJobTimeoutException(updated)
