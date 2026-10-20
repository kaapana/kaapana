"""
Decide a pod's image pull policy from the registry's reachability (kaapana#2149).

With the deploy-time policy ``Always`` (dev mode) the kubelet asks the registry before
every container start, so an unreachable registry leaves pods in ``ImagePullBackOff``
although the image is already on the node. Kubernetes has no "pull if possible" policy,
so the process that creates a pod probes the registry and falls back to ``IfNotPresent``
while it does not answer. A reachable registry keeps ``Always``, so a re-pushed tag is
still picked up.
"""

import logging
import time
import warnings

import requests
import urllib3

logger = logging.getLogger(__name__)

PROBE_TIMEOUT_SECONDS = 2.0
CACHE_SECONDS = 30.0

_cache: dict = {}


def registry_host(image_or_registry: str) -> str:
    """Host of an image reference or registry URL: ``registry.example.com/ns/img:tag``
    and ``https://registry.example.com/ns`` both give ``registry.example.com``.

    Empty for a reference without a registry host, such as ``python:3.11`` or
    ``library/ubuntu``: Docker's rule is that a first component with neither a dot
    nor a port, other than ``localhost``, is a Docker Hub repository, so there is no
    host of that name to probe.
    """
    ref = image_or_registry or ""
    for scheme in ("https://", "http://"):
        if ref.startswith(scheme):
            ref = ref[len(scheme) :]
    first = ref.split("/", 1)[0]
    if "/" in ref:
        # Docker's rule for image references.
        return first if "." in first or ":" in first or first == "localhost" else ""
    # No path: a bare registry URL (registry.example.com, localhost:32000) or a Docker
    # Hub image (python:3.11, ubuntu). A dot or a numeric port marks the host.
    name, _, port = first.partition(":")
    return first if name == "localhost" or "." in name or port.isdigit() else ""


def registry_reachable(host: str, timeout: float = PROBE_TIMEOUT_SECONDS) -> bool:
    """GET ``https://<host>/v2/`` through the process's proxy settings, cached per host.

    Any answer below 500, including the 401 for missing credentials, means the registry
    is up. So does a TLS-layer error: the peer answered, it just does not speak TLS
    there, which is a plain-HTTP registry (``kaapanactl.sh`` supports one as
    ``PLAIN_HTTP``). Certificates are not verified: the question is reachability, not
    trust, and the pod lacks the site CA the node's containerd trusts.
    """
    now = time.monotonic()
    cached = _cache.get(host)
    if cached and now - cached[0] < CACHE_SECONDS:
        return cached[1]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter(
                "ignore", urllib3.exceptions.InsecureRequestWarning
            )
            response = requests.get(
                f"https://{host}/v2/", timeout=timeout, verify=False
            )
        reachable = response.status_code < 500
    except requests.exceptions.SSLError:
        # The connection (or the proxy tunnel) was established and the peer answered
        # at the TLS layer; with verify=False that is a plain-HTTP registry, not an
        # unreachable one. An unreachable registry raises ConnectionError or ProxyError.
        reachable = True
    except requests.RequestException:
        reachable = False
    _cache[host] = (now, reachable)
    return reachable


def effective_pull_policy(configured: str, image_or_registry: str) -> str:
    """The pull policy to put on a pod: ``configured`` unless it is ``Always`` and the
    registry of ``image_or_registry`` does not answer, then ``IfNotPresent``."""
    if configured != "Always":
        return configured
    host = registry_host(image_or_registry)
    if not host or registry_reachable(host):
        return configured
    logger.warning(
        "Registry %s does not answer; using the image already on the node "
        "(imagePullPolicy IfNotPresent) for %s",
        host,
        image_or_registry,
    )
    return "IfNotPresent"
