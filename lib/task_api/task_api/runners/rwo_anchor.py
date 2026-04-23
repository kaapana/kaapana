import logging
import os
import time
from typing import Optional

from kubernetes import client, config
from kubernetes.client import ApiException

ANCHOR_NODE_ANNOTATION = "kaapana.io/anchor-node"
AIRFLOW_RWO_LABEL_SELECTOR = "kaapana.io/airflow-rwo-anchor=true"
WORKFLOW_DATA_PVC_NAME = "workflow-data-pv-claim"

_core_v1_api = None


def _get_core_v1_api() -> client.CoreV1Api:
    global _core_v1_api
    if _core_v1_api is not None:
        return _core_v1_api

    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()

    _core_v1_api = client.CoreV1Api()
    return _core_v1_api


def is_rwo_mode() -> bool:
    return os.getenv("NO_READ_WRITE_MANY_SUPPORT", "False").lower() == "true"


def _services_namespace() -> str:
    return os.getenv("SERVICES_NAMESPACE", "services")


def is_services_namespace(namespace: str) -> bool:
    return namespace == _services_namespace()


def get_anchor_node_from_workflow_pvc(
    namespace: str, logger: logging.Logger = logging
) -> Optional[str]:
    api = _get_core_v1_api()
    try:
        pvc = api.read_namespaced_persistent_volume_claim(
            name=WORKFLOW_DATA_PVC_NAME,
            namespace=namespace,
        )
    except ApiException as e:
        logger.warning(
            "Could not read PVC %s in namespace %s while resolving RWO anchor: %s",
            WORKFLOW_DATA_PVC_NAME,
            namespace,
            e,
        )
        return None

    annotations = pvc.metadata.annotations or {}
    return annotations.get(ANCHOR_NODE_ANNOTATION)


def _workflow_pvc_exists(namespace: str) -> bool:
    api = _get_core_v1_api()
    try:
        api.read_namespaced_persistent_volume_claim(
            name=WORKFLOW_DATA_PVC_NAME,
            namespace=namespace,
        )
        return True
    except ApiException as e:
        if e.status == 404:
            return False
        raise


def set_anchor_node_on_workflow_pvc(
    namespace: str, node_name: str, logger: logging.Logger = logging
) -> Optional[str]:
    api = _get_core_v1_api()
    body = {
        "metadata": {
            "annotations": {
                ANCHOR_NODE_ANNOTATION: node_name,
            }
        }
    }
    try:
        api.patch_namespaced_persistent_volume_claim(
            name=WORKFLOW_DATA_PVC_NAME,
            namespace=namespace,
            body=body,
        )
        logger.info(
            "Set RWO anchor node on %s/%s to %s",
            namespace,
            WORKFLOW_DATA_PVC_NAME,
            node_name,
        )
        return node_name
    except ApiException as e:
        logger.warning(
            "Could not patch PVC %s in namespace %s with RWO anchor node %s: %s",
            WORKFLOW_DATA_PVC_NAME,
            namespace,
            node_name,
            e,
        )
        return None


def _get_services_anchor_pod_node_name(
    logger: logging.Logger = logging,
) -> Optional[str]:
    api = _get_core_v1_api()
    try:
        pods = api.list_namespaced_pod(
            namespace=_services_namespace(),
            label_selector=AIRFLOW_RWO_LABEL_SELECTOR,
        ).items
    except ApiException as e:
        logger.warning("Could not list airflow RWO anchor pods: %s", e)
        return None

    for pod in pods:
        if pod.spec and pod.spec.node_name and pod.status and pod.status.phase == "Running":
            return pod.spec.node_name
    for pod in pods:
        if pod.spec and pod.spec.node_name:
            return pod.spec.node_name
    return None


def ensure_anchor_node(namespace: str, logger: logging.Logger = logging) -> Optional[str]:
    if not is_rwo_mode():
        return None

    anchor_node = get_anchor_node_from_workflow_pvc(namespace=namespace, logger=logger)
    if anchor_node:
        return anchor_node

    if is_services_namespace(namespace):
        anchor_node = _get_services_anchor_pod_node_name(logger=logger)
        if not anchor_node:
            logger.warning(
                "Could not resolve RWO anchor node for services namespace %s", namespace
            )
            return None

        return set_anchor_node_on_workflow_pvc(
            namespace=namespace,
            node_name=anchor_node,
            logger=logger,
        )

    return None


def _hostname_requirement(node_name: str) -> client.V1NodeSelectorRequirement:
    return client.V1NodeSelectorRequirement(
        key="kubernetes.io/hostname",
        operator="In",
        values=[node_name],
    )


def apply_anchor_affinity_to_pod(pod, namespace: str, logger: logging.Logger = logging):
    if not is_rwo_mode():
        return pod

    anchor_node = ensure_anchor_node(namespace=namespace, logger=logger)
    if not anchor_node:
        return pod

    pod.spec.affinity = pod.spec.affinity or client.V1Affinity()
    pod.spec.affinity.node_affinity = (
        pod.spec.affinity.node_affinity or client.V1NodeAffinity()
    )

    required = (
        pod.spec.affinity.node_affinity.required_during_scheduling_ignored_during_execution
    )
    if required is None:
        pod.spec.affinity.node_affinity.required_during_scheduling_ignored_during_execution = (
            client.V1NodeSelector(
                node_selector_terms=[
                    client.V1NodeSelectorTerm(
                        match_expressions=[_hostname_requirement(anchor_node)]
                    )
                ]
            )
        )
        return pod

    required.node_selector_terms = required.node_selector_terms or []
    if not required.node_selector_terms:
        required.node_selector_terms.append(
            client.V1NodeSelectorTerm(
                match_expressions=[_hostname_requirement(anchor_node)]
            )
        )
        return pod

    for term in required.node_selector_terms:
        term.match_expressions = term.match_expressions or []
        if any(
            expression.key == "kubernetes.io/hostname"
            for expression in term.match_expressions
        ):
            continue
        term.match_expressions.append(_hostname_requirement(anchor_node))

    return pod


def initialize_project_anchor_if_needed(
    pod: client.V1Pod,
    namespace: str,
    timeout_seconds: int = 180,
    logger: logging.Logger = logging,
):
    if not is_rwo_mode() or is_services_namespace(namespace):
        return

    existing_anchor = get_anchor_node_from_workflow_pvc(
        namespace=namespace, logger=logger
    )
    if existing_anchor:
        return

    api = _get_core_v1_api()
    pod_name = pod.metadata.name
    deadline = time.time() + timeout_seconds
    observed_node_name = None

    while time.time() < deadline:
        try:
            current_pod = api.read_namespaced_pod(name=pod_name, namespace=namespace)
        except ApiException as e:
            logger.warning(
                "Could not re-read pod %s in namespace %s while initializing RWO project anchor: %s",
                pod_name,
                namespace,
                e,
            )
            time.sleep(1)
            continue

        node_name = current_pod.spec.node_name if current_pod.spec else None
        if node_name:
            observed_node_name = node_name

            try:
                if not _workflow_pvc_exists(namespace=namespace):
                    time.sleep(1)
                    continue
            except ApiException as e:
                logger.warning(
                    "Could not check PVC %s in namespace %s while initializing RWO project anchor: %s",
                    WORKFLOW_DATA_PVC_NAME,
                    namespace,
                    e,
                )
                time.sleep(1)
                continue

            current_anchor = get_anchor_node_from_workflow_pvc(
                namespace=namespace, logger=logger
            )
            if current_anchor:
                return

            if set_anchor_node_on_workflow_pvc(
                namespace=namespace,
                node_name=node_name,
                logger=logger,
            ):
                return

        time.sleep(1)

    logger.warning(
        "Pod %s in namespace %s did not initialize an RWO project anchor within %ss. Last observed node=%s.",
        pod_name,
        namespace,
        timeout_seconds,
        observed_node_name,
    )
