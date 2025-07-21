.. _network:

Network
^^^^^^^

Kaapana uses several components and services to facilitate secure networking. This section provides an overview of the various systems involved in Kaapana’s networking.

.. _network_policies:

Intra Cluster Communication (Network Policies)
**********************************************

The communication of pods within the :ref:`cluster <kubernetes>` is governed by `Kubernetes Network Policies <https://kubernetes.io/docs/concepts/services-networking/network-policies/>`_.
These policies help enforce **network segmentation**, improve **security**, and ensure **explicit access** for required :term:`operators<operator>` only.

General Strategy
----------------
1. Default Deny-All:

  - A baseline policy (`deny-all-traffic`) blocks all ingress and egress traffic by default for all pods in the project namespace.
  - This ensures that no pod can send or receive traffic unless explicitly allowed.

2. Selective Allow Rules:

  - Specific policies selectively **enable communication** between required pods and services.
  - Traffic is only permitted when:

    - Pods have the correct labels (e.g., `network-access-external-ips: "true"`),
    - The destination pod matches a specific label and namespace, and
    - The traffic is on an explicitly allowed port (when applicable).

Policy Descriptions
--------------------

- **deny-all-traffic**
  Denies all incoming and outgoing traffic by default in the project namespace.

- **allow-kube-dns**
  Allows all pods in the project namespace to access the `kube-dns` service in the `kube-system` namespace (needed for DNS resolution).

- **allow-external-ips**
  Allows pods labeled with `network-access-external-ips: "true"` to access external IPs (internet), **except** for a configurable set of internal CIDRs.

- **allow-access-to-squid-proxy**
  Grants pods with `network-access-external-ips: "true"` access to the internal Squid HTTP proxy, allowing controlled internet access through the proxy.

- **allow-access-to-ctp**
  Enables pods labeled with `network-access-ctp: "true"` to communicate with the `ctp` service in the `services` namespace.

- **allow-ingress-from-traefik**
  Allows ingress traffic from the `traefik` service in the `admin` namespace to all pods.

- **allow-opensearch-egress**
  Grants egress access to the `opensearch` service on port 9200 for jobs labeled with `network-access-opensearch: "true"`.

- **allow-keycloak-and-aii-egress**
  Allows the `create-project-user` job to communicate with:
  - `keycloak` service (port 8443) in the `admin` namespace.
  - `access-information-interface` (port 8080) in the `services` namespace.

- **egress-for-processing-containers**
  Grants processing containers (pods labeled `pod-type: "processing-container"`) access to several core services:
  - `keycloak` (8443, 8080)
  - `opensearch` (9200)
  - `dicom-web-filter` (8080)
  - `minio` (9000)
  - `kaapana-backend` (5000)

Security Implications
----------------------
- This strict, **label-based access model** ensures that pods can only communicate with specific, authorized services.
- Unauthorized traffic is dropped by default.
- Outbound internet access is gated through the proxy or through explicit labels and IP filtering.


Ingress
*******

Incoming HTTP requests are redirected to HTTPS and then handled by a :ref:`Traefik <traefik>` reverse proxy.

.. _traefik:

Traefik
-------

Traefik serves as the ingress controller for our system.
Every authenticated request originating from the client-side traverses through Traefik, which efficiently routes it to the appropriate service within the Kubernetes cluster.
Additionally, Traefik applies route-specific middlewares to enhance request handling.
Its user interface provides a comprehensive overview of all routers, services, and middlewares, allowing easy monitoring and management.
Furthermore, Traefik displays warnings or errors, in case of unintended behaviors.


Egress
******

By default egress out of the cluster is blocked in all namespaces (see also :ref:`Network Policies<network_policies>` for special policies of the project namespace).
To enable components (such as **kaapana-federated**) to reach external networks securely, a proxy server is used.
This setup allows Kaapana to maintain secure and auditable outbound connections even in tightly controlled environments.


Squid
-----

`Squid <https://www.squid-cache.org/>`_ is a proxy server used for all outgoing http/https proxy connections.
It is used for caching and logging but also as abstraction layer for various network configurations needed in restricted environments.
Conceptionally, all pods send their outgoing HTTP/HTTPS connections through the internal squid proxy, which is then forwarding them either directly or via a configured upstream proxy (e.g. your institutional proxy) to the outside world.