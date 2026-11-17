.. _existing_cluster:

Deployment on an Existing Kubernetes Cluster
********************************************

By default Kaapana is deployed on a microk8s cluster that ``kaapanactl.sh install`` sets up on the
server itself (see :ref:`server_installation`). Nothing on this page is needed for that case.

This page describes the settings for deploying Kaapana into a Kubernetes cluster that is **not**
the local microk8s, for example a managed Rancher/RKE2 cluster where you only get a few
namespaces and no cluster-wide permissions. Each setting can be used on its own.


Configuration file
==================

All settings below are variables in the function ``load_kaapana_config`` of ``kaapanactl.sh``.
Set them there before running ``kaapanactl.sh deploy``, e.g.:

.. code-block:: bash

   STORAGE_PROVIDER="default"
   RESTRICTED_RBAC=true


Target cluster
==============

``kaapanactl.sh`` deploys to the local microk8s by default. To deploy to another cluster, set
``KUBE_CONTEXT`` to one of the contexts of your kubeconfig (``kubectl config get-contexts``):

.. code-block:: bash

   KUBE_CONTEXT="<context>"


Settings overview
=================

.. list-table::
   :header-rows: 1
   :widths: 22 18 60

   * - Setting (``kaapanactl``) / Helm value
     - Default
     - When to change it / effect
   * - ``IS_MICROK8S`` /
       ``global.is_microk8s``
     - from ``KUBE_CONTEXT``
     - Set automatically: ``false`` if ``KUBE_CONTEXT`` is set. Then container
       images can't be imported from tarballs, ``API_SERVER_CIDR`` is used for the network policies, and
       ``deploy`` asks for an upstream proxy, because the proxy of the machine running
       ``kaapanactl.sh`` doesn't apply to the cluster.
   * - ``KAAPANA_MEMORY_MB`` / ``KAAPANA_CPU_CORES``
     - ``131072`` / ``32``
     - Only used if ``IS_MICROK8S=false``. Memory (MiB) and CPU cores Kaapana is sized for: 70% of the memory
       is split between PACS, Airflow and OpenSearch (requests are a third of the limits), and Airflow runs
       half as many parallel tasks as there are cores. The defaults are the recommended server size (see
       :ref:`requirements`). They are not taken from the cluster, since Kaapana usually shares the nodes
       with other software; set them to the share Kaapana may use. On microk8s they are read from the
       machine running ``kaapanactl.sh``.
   * - ``GPU_SUPPORT``
     - ``false``
     - Only used as a setting if ``IS_MICROK8S=false`` (on microk8s it is detected with ``nvidia-smi``).
       ``true`` requires the NVIDIA GPU operator to be installed on the cluster; ``kaapanactl.sh`` doesn't
       install it there.
   * - ``API_SERVER_CIDR``
     - ``10.0.0.0/8``
     - Only used if ``IS_MICROK8S=false``. Added to ``global.internalCidrs``: the network policies
       allow pods that need the Kubernetes API (Airflow workers, the ``create-project-user`` job) to
       reach this range. Set it to the API server address (``<ip>/32``) to narrow it down.
   * - ``RESTRICTED_RBAC`` /
       ``global.restricted_rbac``
     - ``false``
     - ``true`` if you have no cluster-wide permissions (only namespace-scoped rights, e.g. as a
       Rancher project member). See :ref:`existing_cluster_restricted_rbac`.
   * - ``STORAGE_PROVIDER`` / ``STORAGE_CLASS``
     - ``hostpath`` / ``""``
     - ``STORAGE_PROVIDER="default"`` uses an existing storage class of the cluster for all volumes:
       ``STORAGE_CLASS`` if set, else the cluster's default storage class. ``hostpath`` and
       ``longhorn`` install Kaapana's own storage classes (see :ref:`kaapana_storage`), which needs
       cluster-wide permissions. ``hostpath`` can't be used on a cluster: it keeps the data in a
       directory of a single node, and managed clusters usually forbid hostPath volumes.
   * - ``PREFIX_ALL_NAMESPACES``
     - ``false``
     - ``true`` derives the admin, services and extensions namespaces from the prefix:
       ``<PLATFORM_PREFIX>-admin``, ``-services``, ``-extensions``. Useful if namespace names on the
       cluster must be unique or follow a naming scheme.
   * - ``PUBLIC_PROJECT_ID`` /
       ``global.public_project_id``
     - ``""``
     - UUID of the ``public`` project created at the first deployment (empty: random). Only relevant
       with ``RESTRICTED_RBAC=true``: it makes the project's namespace known in advance. See
       :ref:`existing_cluster_new_project`.
   * - ``EXTRA_MANAGED_NAMESPACES``
     - ``""``
     - Comma-separated namespaces of the projects created after the first deployment, only relevant
       with ``RESTRICTED_RBAC=true``. See :ref:`existing_cluster_new_project`.
   * - ``DICOM_PORT`` /
       ``global.dicom_port``
     - ``11112``
     - The DICOM receiver is exposed as a ``NodePort``. microk8s allows 11112; standard Kubernetes
       only allows node ports in 30000-32767 (e.g. ``31112``). ``0`` disables the NodePort. On
       clusters other than microk8s every node forwards the port (``externalTrafficPolicy:
       Cluster``), so DICOM can be sent to ``HOSTNAME:DICOM_PORT``.


.. _existing_cluster_restricted_rbac:

Restricted RBAC (no cluster-wide permissions)
=============================================

With ``RESTRICTED_RBAC=true`` Kaapana doesn't create anything cluster-scoped and doesn't create
namespaces:

* not created: PriorityClasses (and no ``priorityClassName`` on the pods), LimitRanges, ClusterRoles
  and ClusterRoleBindings, the Traefik CRDs (``deploy`` runs ``helm install --skip-crds``), the
  ``forbid-privileged-pods`` ValidatingAdmissionPolicy.
* instead, the service accounts get Roles/RoleBindings in each namespace of
  ``global.all_managed_namespaces`` (admin, services, extensions, ``<prefix>-project-admin`` and
  ``EXTRA_MANAGED_NAMESPACES``), and Traefik only watches these namespaces.
* ``portal-api`` builds the portal menu only from the ingresses of these namespaces
  (``INGRESS_NAMESPACES``), because it can't list the ingresses of all namespaces.
* the Helm release is installed into the admin namespace instead of ``default``.
* Airflow's KubernetesExecutor only watches the namespaces listed in the ConfigMap
  ``airflow-managed-namespaces`` (services namespace), because it can't watch all namespaces.
* promtail and node-exporter are not deployed: they need hostPath volumes and cluster-wide reads. Logs in
  Grafana/Loki and node metrics (CPU, memory, network utilization) are therefore not available; Prometheus only
  discovers targets in the managed namespaces.

Requirements on the cluster, to be arranged with the cluster administrators:

* The Traefik CRDs (``traefik.io``) of Traefik v3.7 or newer must already be installed on the cluster
  (Kaapana's IngressRoutes use ``spec.ingressClassName``).
* Blocking privileged pods is up to the cluster (e.g. Pod Security Admission), since Kaapana's own
  admission policy is not installed.
* These namespaces must exist **before** the first deployment, and you need full rights in them.
  Besides the namespaces below, this includes the admin project namespace ``<prefix>-project-admin``.

  .. list-table::
     :header-rows: 1

     * - Namespace
       - Default
       - With ``PREFIX_ALL_NAMESPACES=true``
     * - admin (also used for the Helm release)
       - ``admin``
       - ``<prefix>-admin``
     * - services
       - ``services``
       - ``<prefix>-services``
     * - extensions
       - ``extensions``
       - ``<prefix>-extensions``

  ``kaapanactl.sh deploy`` checks this and stops with an error naming the missing namespace.


.. _existing_cluster_new_project:

Creating a project with restricted RBAC
---------------------------------------

Normally Kaapana creates a new namespace for each project and grants its service accounts access to
it. With restricted RBAC it can do neither, so projects can't be created in the UI. The namespace of a
project is ``<prefix>-project-<short id>``, where the short id is the first 8 characters of the
project id (a UUID).

**Initial projects.** At the first deployment Kaapana creates the projects ``admin`` (namespace
``<prefix>-project-admin``) and ``public``. Set ``PUBLIC_PROJECT_ID`` to a UUID (e.g. from ``uuidgen``)
to know the ``public`` namespace in advance, and create it before deploying. ``kaapanactl.sh deploy``
checks that it exists and handles it like the admin project namespace.

**Further projects** are created with a script while Kaapana is running:

.. code-block:: bash

   ./utils/create-restricted-rbac-project.sh

It asks for the project name, generates the project id and names the namespace that you then create
on the cluster (e.g. in Rancher, in the same Rancher project as the other Kaapana namespaces). Once
you confirm that the namespace exists, the script grants Kaapana access to it, creates the project and
makes the project's applications reachable. After you have checked the project under *Projects* in
the UI, it prints the namespace to add to ``EXTRA_MANAGED_NAMESPACES`` in ``kaapanactl.sh``, so the
next deployment keeps the project's access rights.
