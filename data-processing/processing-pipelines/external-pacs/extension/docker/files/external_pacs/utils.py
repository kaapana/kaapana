import base64
import hashlib
import logging
from typing import Dict, List

from kaapana.kubetools.kube_client import get_kube_client
from kubernetes import client

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__file__)


def create_k8s_secret(
    secret_name: str,
    secret_data: Dict[str, str],
    namespace: str = "services",
):
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
        logger.info("Secret created successfully")
    except client.ApiException as e:
        logger.error(f"Secret '{secret_name}' creation FAILED: {e}.")
        if e.status == 409:  # already exists
            return
        else:
            raise e


def delete_k8s_secret(secret_name: str, namespace: str = "services"):
    api_instance, _, _ = get_kube_client()

    try:
        api_instance.delete_namespaced_secret(name=secret_name, namespace=namespace)
        logger.info(
            f"Secret '{secret_name}' deleted successfully from namespace '{namespace}'."
        )
    except client.ApiException as e:
        if e.status == 404:
            logger.warning(
                f"Secret '{secret_name}' not found in namespace '{namespace}'."
            )
        else:
            logger.error(f"Failed to delete secret '{secret_name}': {e}.")


def get_all_k8s_secrets(namespace: str = "services") -> List[Dict[str, str]]:
    api_instance, _, _ = get_kube_client()

    try:
        secrets = api_instance.list_namespaced_secret(namespace=namespace)
        all_secrets = []

        for secret in secrets.items:
            decoded_data = {
                key: base64.b64decode(value).decode("utf-8")
                for key, value in secret.data.items()
            }
            all_secrets.append(decoded_data)

        logger.info(f"All secrets retrieved successfully from namespace '{namespace}'.")
        return all_secrets
    except client.ApiException as e:
        logger.error(f"Failed to retrieve secrets from namespace '{namespace}': {e}.")
        return []


def get_k8s_secret(secret_name: str, namespace: str = "services"):
    api_instance, _, _ = get_kube_client()

    try:
        secret = api_instance.read_namespaced_secret(
            name=secret_name, namespace=namespace
        )
        decoded_data = {
            key: base64.b64decode(value).decode("utf-8")
            for key, value in secret.data.items()
        }
        logger.info(
            f"Secret '{secret_name}' retrieved successfully from namespace '{namespace}'."
        )
        return decoded_data
    except client.ApiException as e:
        if e.status == 404:
            logger.warning(
                f"Secret '{secret_name}' not found in namespace '{namespace}'."
            )
        else:
            logger.error(f"Failed to retrieve secret '{secret_name}': {e}.")
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
