from kubernetes import client, config
from kubernetes.stream import stream
from contextlib import contextmanager
from typing import Generator
import io
import uuid
import time
import tarfile
import logging


class KubernetsUtils:
    logger = logging.getLogger(__name__)

    @classmethod
    @contextmanager
    def extract_file_from_image(
        cls,
        image: str,
        file_path: str,
        namespace: str = "default",
        registry_secret: str | None = None,
    ) -> Generator[io.BytesIO, None, None]:
        config.load_config()

        core = client.CoreV1Api()
        name = f"extract-file-{uuid.uuid4().hex[:8]}"

        pod = client.V1Pod(
            metadata=client.V1ObjectMeta(name=name),
            spec=client.V1PodSpec(
                restart_policy="Never",
                containers=[
                    client.V1Container(
                        name=name,
                        image=image,
                        command=["sleep", "3600"],
                    )
                ],
                image_pull_secrets=(
                    [client.V1LocalObjectReference(name=registry_secret)]
                    if registry_secret
                    else None
                ),
            ),
        )

        try:
            core.create_namespaced_pod(namespace=namespace, body=pod)
            KubernetsUtils._wait_for_pod_ready(core, name, namespace)
            cls.logger.info(f"Pod {name} is ready")

            exec_command = [
                "tar",
                "cf",
                "-",
                "-C",
                "/",  # Start from root
                file_path.lstrip("/"),
            ]

            tar_bytes = stream(
                core.connect_get_namespaced_pod_exec,
                name=name,
                namespace=namespace,
                command=exec_command,
                container=name,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False,
                _preload_content=False,
            )

            file_stream = io.BytesIO()
            while tar_bytes.is_open():
                tar_bytes.update(timeout=1)
                if tar_bytes.peek_stdout():
                    out = tar_bytes.read_stdout()
                    file_stream.write(out.encode("utf-8"))
                if tar_bytes.peek_stderr():
                    err = tar_bytes.read_stderr()
                    cls.logger.info(f"[stderr]: {err}")
            tar_bytes.close()
            file_stream.seek(0)

            with tarfile.open(fileobj=file_stream, mode="r:") as tar:
                member = tar.getmembers()[0]
                extracted = tar.extractfile(member)
                if extracted:
                    yield io.BytesIO(extracted.read())
                else:
                    raise Exception("Failed to extract file from tar")
        finally:
            try:
                core.delete_namespaced_pod(
                    name=name, namespace=namespace, body=client.V1DeleteOptions()
                )
            except Exception as e:
                cls.logger.warning(f"Failed to delete pod {name}: {e}")

    @staticmethod
    def _wait_for_pod_ready(
        core_api: client.CoreV1Api, pod_name: str, namespace: str, timeout: int = 60
    ):
        start = time.time()
        while True:
            pod = core_api.read_namespaced_pod(name=pod_name, namespace=namespace)
            phase = pod.status.phase
            if phase in ["Running", "Succeeded"]:
                return
            if phase == "Failed":
                raise Exception("Pod failed to start.")
            if time.time() - start > timeout:
                raise TimeoutError("Pod did not become ready in time.")
            time.sleep(1)
