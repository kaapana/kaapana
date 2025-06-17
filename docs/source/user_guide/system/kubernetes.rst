.. _kubernetes:

Kubernetes
^^^^^^^^^^

:term:`Kubernetes<kubernetes>` is the core of the whole platform.
You can interact with Kubernetes either via the Kubernetes Dashboard, accessible on the *System* menu in the web interface or directly via the terminal using `kubectl` on the server. 
In case anything on the platform is not working, Kubernetes is the first place to go.
To debug using Kubernetes, refer to :ref:`faq_debug_kubernetes`.


Dashboard user permissions
****************************
We've implemented a new ClusterRole, `kaapana-kube-dashboard-production`, specifically tailored for the Kubernetes Dashboard. 
When the platform is deployed in production mode (i.e., :code:`DEV_MODE=false`), the ServiceAccount for the Kubernetes Dashboard is associated with this role. 
This ClusterRole grants restricted access to the Kubernetes API, enabling essential actions such as viewing, watching, listing, and deleting pods, as well as managing secrets. 
For ressources apart from pods and secrets only fundamental operations like viewing and listing are permitted. 
This enhancement serves to improve security measures for production environments.

In non-production systems the Kubernetes Dasboard can be used for unrestricted operations on Kubernetes resources.

.. _network_policies:

Network Policies
*****************
The following Kubernetes Network Policies define and control how pods within the Kaapana platform can communicate with each other and with external services. 
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
