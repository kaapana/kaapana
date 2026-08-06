"""Only module that talks to the kubernetes API server.

kubernetes is imported lazily so importing the app (and running the unit tests)
needs neither the package nor a kubeconfig.
"""

import asyncio

from app.menu import IngressInfo

_config_loaded = False


def _load_config() -> None:
    from kubernetes import config
    from kubernetes.config import ConfigException

    global _config_loaded
    if not _config_loaded:
        try:
            config.load_incluster_config()
        except ConfigException:
            # local dev outside the cluster
            config.load_kube_config()
        _config_loaded = True


def _list_ingresses_blocking() -> list[IngressInfo]:
    from kubernetes import client

    _load_config()
    infos = []
    for ingress in client.NetworkingV1Api().list_ingress_for_all_namespaces().items:
        first_path = None
        for rule in ingress.spec.rules or []:
            if rule.http and rule.http.paths:
                first_path = rule.http.paths[0].path
                break
        infos.append(
            IngressInfo(
                namespace=ingress.metadata.namespace,
                name=ingress.metadata.name,
                annotations=dict(ingress.metadata.annotations or {}),
                first_path=first_path,
            )
        )
    return infos


async def list_ingresses() -> list[IngressInfo]:
    # run the sync kubernetes client off the event loop
    return await asyncio.to_thread(_list_ingresses_blocking)
