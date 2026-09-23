import os

from kubernetes import client

# Label of the pod that owns the ReadWriteOnce volumes of a namespace
# (services: airflow-scheduler, admin: kube-helm, project: project-runtime).
RWO_ANCHOR_LABEL = "kaapana.io/rwo-anchor"


def is_rwo_mode() -> bool:
    return os.getenv("NO_READ_WRITE_MANY_SUPPORT", "False").lower() == "true"


def _anchor_affinity_term() -> client.V1PodAffinityTerm:
    # Without namespaces/namespaceSelector the term only matches pods in the pod's own namespace.
    return client.V1PodAffinityTerm(
        label_selector=client.V1LabelSelector(
            match_expressions=[
                client.V1LabelSelectorRequirement(
                    key=RWO_ANCHOR_LABEL, operator="In", values=["true"]
                )
            ]
        ),
        topology_key="kubernetes.io/hostname",
    )


def apply_anchor_affinity_to_pod(pod: client.V1Pod) -> client.V1Pod:
    """Schedule the pod on the node of its namespace's RWO anchor pod."""
    if not is_rwo_mode():
        return pod

    pod.spec.affinity = pod.spec.affinity or client.V1Affinity()
    pod.spec.affinity.pod_affinity = (
        pod.spec.affinity.pod_affinity or client.V1PodAffinity()
    )
    pod_affinity = pod.spec.affinity.pod_affinity
    terms = (
        pod_affinity.required_during_scheduling_ignored_during_execution or []
    )
    already_set = any(
        expression.key == RWO_ANCHOR_LABEL
        for term in terms
        if term.label_selector and term.label_selector.match_expressions
        for expression in term.label_selector.match_expressions
    )
    if not already_set:
        terms.append(_anchor_affinity_term())
    pod_affinity.required_during_scheduling_ignored_during_execution = terms
    return pod
