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
import base64
import hashlib
import os
import traceback
from typing import Dict

from app.logger import get_logger
from kubernetes import client
from six import PY2

logger = get_logger(__name__)


SERVICES_NAMESPACE = os.getenv("SERVICES_NAMESPACE")


def _load_kube_config(in_cluster, cluster_context, config_file):
    from kubernetes import client, config

    if in_cluster:
        config.load_incluster_config()
    else:
        config.load_kube_config(config_file=config_file, context=cluster_context)
    if PY2:
        # For connect_get_namespaced_pod_exec
        from kubernetes.client import Configuration

        configuration = Configuration()
        configuration.assert_hostname = False
        Configuration.set_default(configuration)
    return client.CoreV1Api(), client.BatchV1Api(), client.NetworkingV1Api()


def get_kube_client(in_cluster=True, cluster_context=None, config_file=None):
    return _load_kube_config(in_cluster, cluster_context, config_file)


def create_k8s_secret(
    secret_name: str,
    secret_data: Dict[str, str],
    namespace: str = SERVICES_NAMESPACE,
) -> bool:
    api_instance, _, _ = get_kube_client()

    encoded_credentials = {}
    for key, value in secret_data.items():
        encoded_credentials[key] = base64.b64encode(value.encode("utf-8")).decode(
            "utf-8"
        )

    secret = client.V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=client.V1ObjectMeta(name=secret_name),
        data=encoded_credentials,
        type="Opaque",  # Use "Opaque" type for generic secret data
    )
    try:
        api_instance.create_namespaced_secret(namespace, secret)
        return True
    except client.ApiException as e:
        if e.status == 409:  # already exists
            return True

        else:
            logger.error(f"Failed to create secret: {secret_name}")
            logger.error(e)
            logger.error(traceback.format_exc())
            return False


def delete_k8s_secret(secret_name: str, namespace: str = SERVICES_NAMESPACE) -> bool:
    api_instance, _, _ = get_kube_client()

    try:
        api_instance.delete_namespaced_secret(name=secret_name, namespace=namespace)
        logger.info(
            f"Secret '{secret_name}' deleted successfully from namespace '{namespace}'."
        )
        return True
    except client.ApiException as e:
        if e.status == 404:  # Not found in the namespace
            return True
        else:
            logger.error(f"Failed to delete secret: {secret_name}")
            logger.error(e)
            logger.error(traceback.format_exc())
            return False


def get_k8s_secret(secret_name: str, namespace: str = SERVICES_NAMESPACE):
    api_instance, _, _ = get_kube_client()

    try:
        secret = api_instance.read_namespaced_secret(
            name=secret_name, namespace=namespace
        )
        decoded_data = {
            key: base64.b64decode(value).decode("utf-8")
            for key, value in secret.data.items()
        }
        return decoded_data
    except client.ApiException as e:
        if e.status == 404:
            logger.warning(f"Secret not found in namespace")
        else:
            logger.error(f"Secret cannot be retrieved from the namespace")
        return None


def hash_secret_name(name: str):
    # Calculate SHA-256 hash of the endpoint URL
    hash_object = hashlib.sha256(name.encode())
    hash_hex = hash_object.hexdigest()

    # Convert hexadecimal hash to a valid Kubernetes secret name
    valid_chars = set("abcdefghijklmnopqrstuvwxyz0123456789.-")
    secret_name = "".join(c if c in valid_chars else "-" for c in hash_hex.lower())

    # Ensure the secret name starts with a letter as per Kubernetes naming convention
    if not secret_name[0].isalpha():
        secret_name = (
            "s-" + secret_name
        )  # prepend 's-' if the name starts with a non-letter

    return secret_name[:63]  # Kubernetes secret names are limited to 63 characters
