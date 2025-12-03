from datetime import timedelta
import os
import kubernetes
import logging
import time
from pathlib import Path
from kaapana.blueprints.kaapana_global_variables import (
    AIRFLOW_WORKFLOW_DIR,
    BATCH_NAME,
    DEFAULT_REGISTRY,
    KAAPANA_BUILD_VERSION,
    PULL_POLICY_IMAGES,
)
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapanapy.helper import get_project_user_access_token

logger = logging.getLogger(__name__)


class KubernetesHelper:
    def __init__(self, namespace: str):
        kubernetes.config.load_config()
        self.core = kubernetes.client.CoreV1Api()
        self.batch = kubernetes.client.BatchV1Api()
        self.namespace = namespace

    def create_pvc_for_folder(self, host_path: Path, read_only: bool = False) -> str:
        """Creates a volume PersistentVolume and a PersistentVolumeClaim for the given hostpath and returns the PVC name"""
        name = f"{host_path.name}-{os.urandom(4).hex()}-pvc"
        pv_name = name.replace("-pvc", "-pv")
        storage = "1Mi"

        # Create PersistentVolume
        pv_spec = kubernetes.client.V1PersistentVolumeSpec(
            capacity={"storage": storage},
            access_modes=["ReadWriteOnce"] if not read_only else ["ReadOnlyMany"],
            persistent_volume_reclaim_policy="Retain",
            volume_mode="Filesystem",
            storage_class_name="",  # required for static binding
            host_path=kubernetes.client.V1HostPathVolumeSource(
                path=str(host_path), type="DirectoryOrCreate"
            ),
        )

        pv_metadata = kubernetes.client.V1ObjectMeta(
            name=pv_name, namespace=self.namespace
        )
        pv = kubernetes.client.V1PersistentVolume(
            api_version="v1",
            kind="PersistentVolume",
            metadata=pv_metadata,
            spec=pv_spec,
        )

        # Create PersistentVolumeClaim
        pvc_spec = kubernetes.client.V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteOnce"] if not read_only else ["ReadOnlyMany"],
            resources=kubernetes.client.V1ResourceRequirements(
                requests={"storage": storage}
            ),
            storage_class_name="",  # must match PV (empty) for static binding
            volume_name=pv_name,  # bind explicitly to the PV above
        )

        pvc_metadata = kubernetes.client.V1ObjectMeta(
            name=name, namespace=self.namespace
        )
        pvc = kubernetes.client.V1PersistentVolumeClaim(
            api_version="v1",
            kind="PersistentVolumeClaim",
            metadata=pvc_metadata,
            spec=pvc_spec,
        )

        try:
            # Create PV
            self.core.create_persistent_volume(body=pv)
            logger.info(f"Created PersistentVolume: {pv_name}")

            # Create PVC
            self.core.create_namespaced_persistent_volume_claim(
                namespace=self.namespace, body=pvc
            )
            logger.info(f"Created PersistentVolumeClaim: {name}")

        except kubernetes.client.ApiException as e:
            logger.error(f"Failed to create PV/PVC: {e}")
            raise

        return name

    def spawn_job(
        self,
        image: str,
        command: str,
        args: list[str],
        input_pvc_name: str,
        output_pvc_name: str,
        image_pull_secrets: list[str] | None = None,
        configmap_name: str | None = None,
        configmap_key: str | None = None,
        configmap_mount_path: str | None = None,
    ) -> str:
        """Creates and starts a Kubernetes Job for ingestion processing"""
        job_name = f"ingestion-run-{os.urandom(4).hex()}"

        # Prepare volume mounts
        volume_mounts = [
            kubernetes.client.V1VolumeMount(
                name="input",
                mount_path="/input",
                read_only=True,
            ),
            kubernetes.client.V1VolumeMount(
                name="output",
                mount_path="/output",
                read_only=False,
            ),
        ]

        # Prepare volumes
        volumes = [
            kubernetes.client.V1Volume(
                name="input",
                persistent_volume_claim=kubernetes.client.V1PersistentVolumeClaimVolumeSource(
                    claim_name=input_pvc_name
                ),
            ),
            kubernetes.client.V1Volume(
                name="output",
                persistent_volume_claim=kubernetes.client.V1PersistentVolumeClaimVolumeSource(
                    claim_name=output_pvc_name
                ),
            ),
        ]

        # Add configmap volume and mount if specified
        if configmap_name and configmap_key and configmap_mount_path:
            volumes.append(
                kubernetes.client.V1Volume(
                    name="config-volume",
                    config_map=kubernetes.client.V1ConfigMapVolumeSource(
                        name=configmap_name,
                        items=[
                            kubernetes.client.V1KeyToPath(
                                key=configmap_key, path=configmap_mount_path.lstrip("/")
                            )
                        ],
                    ),
                )
            )
            volume_mounts.append(
                kubernetes.client.V1VolumeMount(
                    name="config-volume",
                    mount_path=configmap_mount_path,
                    read_only=True,
                    sub_path=configmap_mount_path.lstrip("/"),
                )
            )

        # Prepare image pull secrets
        image_pull_secrets_refs = None
        if image_pull_secrets:
            image_pull_secrets_refs = [
                kubernetes.client.V1LocalObjectReference(name=secret)
                for secret in image_pull_secrets
            ]

        # Create job specification
        job_spec = kubernetes.client.V1JobSpec(
            backoff_limit=0,
            template=kubernetes.client.V1PodTemplateSpec(
                metadata=kubernetes.client.V1ObjectMeta(
                    labels={"app": "ingestion-run"}
                ),
                spec=kubernetes.client.V1PodSpec(
                    service_account_name="ingestion-sa",
                    restart_policy="Never",
                    image_pull_secrets=image_pull_secrets_refs,
                    containers=[
                        kubernetes.client.V1Container(
                            name="pipeline",
                            image=image,
                            image_pull_policy=PULL_POLICY_IMAGES,
                            command=[command],
                            args=args,
                            env=[
                                kubernetes.client.V1EnvVar(
                                    name="NAMESPACE",
                                    value_from=kubernetes.client.V1EnvVarSource(
                                        field_ref=kubernetes.client.V1ObjectFieldSelector(
                                            field_path="metadata.namespace"
                                        )
                                    ),
                                ),
                                kubernetes.client.V1EnvVar(
                                    name="INPUT_PVC_NAME", value=input_pvc_name
                                ),
                                kubernetes.client.V1EnvVar(
                                    name="OUTPUT_PVC_NAME", value=output_pvc_name
                                ),
                                kubernetes.client.V1EnvVar(
                                    name="INPUT_PVC_ROOT", value="/input"
                                ),
                                kubernetes.client.V1EnvVar(
                                    name="OUTPUT_PVC_ROOT", value="/output"
                                ),
                            ],
                            volume_mounts=volume_mounts,
                        )
                    ],
                    volumes=volumes,
                ),
            ),
        )

        job_metadata = kubernetes.client.V1ObjectMeta(
            name=job_name, namespace="ingestion"
        )

        job = kubernetes.client.V1Job(
            api_version="batch/v1", kind="Job", metadata=job_metadata, spec=job_spec
        )

        try:
            self.batch.create_namespaced_job(namespace="ingestion", body=job)
            logger.info(f"Created Job: {job_name}")
            return job_name
        except kubernetes.client.ApiException as e:
            logger.error(f"Failed to create Job: {e}")
            raise

    def wait_for_job(self, job_name: str):
        """Waits for the current job to complete and outputs job logs in real-time"""
        logger.info(f"Waiting for job {job_name} to complete...")

        last_log_lines = {}  # Track last log line for each pod to avoid duplicates
        job_failed = False

        try:
            while True:
                try:
                    job = self.batch.read_namespaced_job_status(
                        name=job_name, namespace=self.namespace
                    )

                    self._stream_job_logs(job_name, last_log_lines)

                    # Check job status
                    if job.status.succeeded:
                        logger.info(f"Job {job_name} completed successfully")
                        # Get any remaining logs
                        self._stream_job_logs(job_name, last_log_lines)
                        break
                    elif job.status.failed:
                        logger.error(f"Job {job_name} failed")
                        # Get any remaining logs
                        self._stream_job_logs(job_name, last_log_lines)
                        job_failed = True
                        break
                    elif job.status.active:
                        time.sleep(5)  # Reduced wait time for more frequent log updates
                    else:
                        logger.info(f"Job {job_name} status unknown, waiting...")
                        time.sleep(5)

                except kubernetes.client.ApiException as e:
                    logger.error(f"Error checking job status: {e}")
                    break

        finally:
            # Clean up the job in any case
            try:
                self.batch.delete_namespaced_job(
                    name=job_name,
                    namespace=self.namespace,
                    body=kubernetes.client.V1DeleteOptions(
                        propagation_policy="Background"
                    ),
                )
                logger.info(f"Deleted job {job_name}")
            except kubernetes.client.ApiException as e:
                logger.error(f"Failed to delete job {job_name}: {e}")

        # Throw exception if job failed, after cleanup
        if job_failed:
            raise RuntimeError(f"Kubernetes job {job_name} failed")

    def _stream_job_logs(self, job_name: str, last_log_lines: dict):
        """Stream logs from job pods, avoiding duplicates"""
        try:
            # Get pods for this job
            pods = self.core.list_namespaced_pod(
                namespace=self.namespace, label_selector=f"job-name={job_name}"
            )

            for pod in pods.items:
                pod_name = pod.metadata.name

                # Skip if pod is not ready yet
                if not pod.status.phase or pod.status.phase in ["Pending", "Unknown"]:
                    continue

                try:
                    # Get pod logs
                    logs = self.core.read_namespaced_pod_log(
                        name=pod_name, namespace=self.namespace, container="pipeline"
                    )

                    if logs:
                        log_lines = logs.split("\n")

                        # Get the last logged line for this pod
                        last_line_index = last_log_lines.get(pod_name, -1)

                        # Output only new lines
                        for i, line in enumerate(log_lines):
                            if i > last_line_index and line.strip():
                                logger.info(f"[{pod_name}] {line}")

                        # Update the last processed line index
                        if log_lines:
                            last_log_lines[pod_name] = len(log_lines) - 1

                except kubernetes.client.ApiException as e:
                    # Only log error if it's not a "not found" error (pod might not be ready yet)
                    if e.status != 404:
                        logger.error(f"Failed to get logs for pod {pod_name}: {e}")

        except kubernetes.client.ApiException as e:
            logger.error(f"Failed to list pods for job {job_name}: {e}")

    def destroy_pvc_for_folder(self, name: str):
        """Destroys the PVC and PV created for the folder"""
        pv_name = name.replace("-pvc", "-pv")

        try:
            # Delete PVC first
            self.core.delete_namespaced_persistent_volume_claim(
                name=name, namespace=self.namespace
            )
            logger.info(f"Deleted PersistentVolumeClaim: {name}")

            # Delete PV
            self.core.delete_persistent_volume(name=pv_name)
            logger.info(f"Deleted PersistentVolume: {pv_name}")

        except kubernetes.client.ApiException as e:
            logger.error(f"Failed to delete PV/PVC: {e}")
            raise


class LocalIngestionOperator(KaapanaPythonBaseOperator):
    def __init__(
        self,
        dag,
        input_operator,
        batch_name=None,
        airflow_workflow_dir=None,
        parallel_id=None,
        **kwargs,
    ):
        super().__init__(
            dag=dag,
            input_operator=input_operator,
            name="ingestion",
            python_callable=self.ingestion,
            batch_name=batch_name,
            parallel_id=parallel_id,
            airflow_workflow_dir=airflow_workflow_dir,
            execution_timeout=timedelta(minutes=20),
            **kwargs,
        )

    def ingestion(self, ds, **kwargs):
        dag_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id
        # TODO add project_id and user_id to ingested data
        # project_id = kwargs["dag_run"]["conf"]["project_form"]["id"]
        # username = kwargs["dag_run"]["conf"]["workflow_form"]["username"]
        # import kaapanapy
        # user_id = kaapanapy.utils.get_user_id(username)
        access_token = get_project_user_access_token()

        batch_dir = dag_dir / BATCH_NAME
        if batch_dir.exists():
            # batch execution
            batch_folders = sorted(f for f in batch_dir.iterdir())
        else:
            # single execution
            batch_folders = [dag_dir]

        k8s_helper = KubernetesHelper(namespace="ingestion")

        if len(batch_folders) == 0:
            logger.warning("No batch in input %s", batch_dir)
            return 1

        for batch_folder in batch_folders:
            # Translate folder in container to folder on host
            host_batch_folder = Path(
                str(batch_folder).replace(
                    AIRFLOW_WORKFLOW_DIR, os.getenv("DATADIR", "")
                )
            )
            input_folder = (
                host_batch_folder / self.operator_in_dir
            )  # self.input_operator.operator_out_dir
            output_folder = host_batch_folder / "ingestion"

            pvc_input = k8s_helper.create_pvc_for_folder(input_folder)
            pvc_output = k8s_helper.create_pvc_for_folder(output_folder)

            try:
                # image="docker.io/library/ubuntu:latest"
                image = f"{DEFAULT_REGISTRY}/extractorctl:{KAAPANA_BUILD_VERSION}"
                image_pull_secrets = ["registry-secret"]
                job_name = k8s_helper.spawn_job(
                    image=image,
                    image_pull_secrets=image_pull_secrets,
                    # command="/bin/bash",
                    # args=[
                    #     "-c",
                    #     "ls -la /input > /output/input_listing.txt && echo 'Processing complete' > /output/status.txt",
                    # ],
                    command="python",
                    args=[
                        "-m",
                        "extractors.extractorctl",
                        "ingestion",
                        "run",
                        "/input",
                        "/output",
                        "--config",
                        "/config.yaml",
                        "--runtime",
                        "kubernetes",
                        "--input-host-dir",
                        f"{input_folder}",
                        "--run-host-dir",
                        f"{output_folder}",
                        "--namespace",
                        "ingestion",
                        "--access-token",
                        access_token,
                    ],
                    input_pvc_name=pvc_input,
                    output_pvc_name=pvc_output,
                    configmap_name="ingestion-cm",
                    configmap_key="config.yaml",
                    configmap_mount_path="/config.yaml",
                )
                k8s_helper.wait_for_job(job_name)

            finally:
                # Ensure PVCs are always cleaned up, regardless of job success or failure
                try:
                    k8s_helper.destroy_pvc_for_folder(pvc_input)
                except Exception as e:
                    logger.error(f"Failed to cleanup input PVC {pvc_input}: {e}")

                try:
                    k8s_helper.destroy_pvc_for_folder(pvc_output)
                except Exception as e:
                    logger.error(f"Failed to cleanup output PVC {pvc_output}: {e}")
