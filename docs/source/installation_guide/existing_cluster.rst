.. _existing_cluster:

Deployment on an Existing Kubernetes Cluster
********************************************

By default Kaapana is deployed on a microk8s cluster that ``kaapanactl.sh install`` sets up on the
server itself (see :ref:`server_installation`). Nothing on this page is needed for that case.

This page describes the settings for deploying Kaapana into a Kubernetes cluster that is **not**
the local microk8s, for example a managed Rancher/RKE2 cluster where you only get a few
namespaces and no cluster-wide permissions. Each setting can be used on its own; the
:ref:`example <existing_cluster_example>` at the end shows a typical managed-cluster combination.


Configuration file
==================

All settings below are variables in the function ``load_kaapana_config`` of ``kaapanactl.sh``.
Set them there before running ``kaapanactl.sh deploy``, e.g.:

.. code-block:: bash

   RESTRICTED_RBAC=true
   EXTERNAL_INGRESS="nginx"


Target cluster
==============

``kaapanactl.sh`` uses ``kubectl`` (or ``microk8s.kubectl`` if no ``kubectl`` is installed) with the
**current kubeconfig context**. To deploy to another cluster, switch the context first:

.. code-block:: bash

   kubectl config get-contexts
   kubectl config use-context <context>

``IS_MICROK8S`` is detected from that context: it is ``false`` if the context's API server is not on
port 16443 (the microk8s API server port), otherwise ``true``. Without a readable kubeconfig it stays
``true``. Set ``IS_MICROK8S`` in ``load_kaapana_config`` to override the detection.


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
     - detected
     - ``false`` for any cluster other than the local microk8s. Then kube-helm doesn't mount the
       microk8s containerd socket (so container images can't be imported from tarballs), the
       microk8s-specific network ranges aren't detected (``API_SERVER_CIDR`` is used instead), and
       ``deploy`` asks for an upstream proxy, because the proxy of the machine running
       ``kaapanactl.sh`` doesn't apply to the cluster.
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
   * - ``EXTERNAL_INGRESS`` /
       ``global.external_ingress``
     - ``""``
     - Ingress class of the cluster's ingress controller (e.g. ``traefik``, ``nginx``) if the
       cluster already has one in front of Kaapana. See :ref:`existing_cluster_external_ingress`.
   * - ``NO_READ_WRITE_MANY_SUPPORT`` /
       ``global.no_read_write_many_support``
     - ``false``
     - ``true`` if the storage class only supports ``ReadWriteOnce`` volumes (typical for block
       storage). See :ref:`existing_cluster_rwo`.
   * - ``STORAGE_PROVIDER`` / ``STORAGE_CLASS``
     - ``hostpath`` / ``""``
     - ``STORAGE_PROVIDER="default"`` uses an existing storage class of the cluster for all volumes:
       ``STORAGE_CLASS`` if set, else the cluster's default storage class. ``hostpath`` and
       ``longhorn`` install Kaapana's own storage classes (see :ref:`kaapana_storage`), which needs
       cluster-wide permissions.
   * - ``PLATFORM_PREFIX`` /
       ``global.platform_prefix``
     - asked on deploy
     - Always required (``--platform-prefix``). Project namespaces are named
       ``<PLATFORM_PREFIX>-project-<short id>``.
   * - ``PREFIX_ALL_NAMESPACES``
     - ``false``
     - ``true`` derives the admin, services and extensions namespaces from the prefix:
       ``<PLATFORM_PREFIX>-admin``, ``-services``, ``-extensions``. Useful if namespace names on the
       cluster must be unique or follow a naming scheme.
   * - ``EXTRA_MANAGED_NAMESPACES``
     - ``""``
     - Comma-separated project namespaces, only relevant with ``RESTRICTED_RBAC=true``. See
       :ref:`existing_cluster_new_project`.
   * - ``DICOM_PORT`` /
       ``global.dicom_port``
     - ``11112``
     - The DICOM receiver is exposed as a ``NodePort``. microk8s allows 11112; standard Kubernetes
       only allows node ports in 30000-32767 (e.g. ``31112``). ``0`` disables the NodePort.


.. _existing_cluster_restricted_rbac:

Restricted RBAC (no cluster-wide permissions)
=============================================

With ``RESTRICTED_RBAC=true`` Kaapana doesn't create anything cluster-scoped and doesn't create
namespaces:

* not created: PriorityClasses (and no ``priorityClassName`` on the pods), LimitRanges, ClusterRoles
  and ClusterRoleBindings, the Traefik CRDs, the ``forbid-privileged-pods``
  ValidatingAdmissionPolicy.
* instead, the service accounts get Roles/RoleBindings in each namespace of
  ``global.all_managed_namespaces`` (admin, services, extensions, ``<prefix>-project-admin`` and
  ``EXTRA_MANAGED_NAMESPACES``), and Traefik only watches these namespaces.
* the Helm release is installed into the admin namespace instead of ``default``.
* Airflow's KubernetesExecutor only watches the namespaces listed in the ConfigMap
  ``airflow-managed-namespaces`` (services namespace), because it can't watch all namespaces.

Requirements on the cluster, to be arranged with the cluster administrators:

* The Traefik CRDs (``traefik.io``) must already be installed on the cluster.
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

Normally Kaapana creates a new namespace for each project. With restricted RBAC this is not possible,
so every new project needs manual steps:

#. Create the project in the Kaapana UI. It fails, because the namespace
   ``<prefix>-project-<short id>`` doesn't exist. The namespace name is in the error logged by the
   ``access-information-interface`` and ``kube-helm`` pods. The short id is the first 8 characters of
   the project id.
#. Create this namespace on the cluster (e.g. in Rancher, in the same Rancher project as the other
   Kaapana namespaces).
#. Give Kaapana's service accounts access to the new namespace:

   .. code-block:: bash

      ADMIN_NAMESPACE=<admin ns> SERVICES_NAMESPACE=<services ns> \
        ./utils/apply-managed-project-namespace-rbac.sh <prefix>-project-<short id>

#. Create the project again with the **same name** in the Kaapana UI. Kaapana reuses the existing
   project and completes the setup. The ``create-project-user`` job adds the namespace to the
   ConfigMap ``airflow-managed-namespaces`` and restarts the Airflow scheduler, so workflows can
   run in the new project.

Traefik only watches the namespaces it got at startup, so applications started in the new project
(e.g. JupyterLab from a workflow) are not reachable yet. To add the namespace without re-deploying:

#. Add it to ``EXTRA_MANAGED_NAMESPACES`` in ``kaapanactl.sh``, so that the next deployment keeps it.
#. Add it to the two namespace lists of the running Traefik:

   .. code-block:: bash

      kubectl -n <admin ns> edit deployment traefik
      # append ,<prefix>-project-<short id> to the arguments
      #   --providers.kubernetesingress.namespaces=...
      #   --providers.kubernetescrd.namespaces=...

   Saving the change restarts the Traefik pod with the new list.

At the next deployment the Helm charts take over the namespace's Traefik configuration and RBAC
from step 3.
.. _existing_cluster_external_ingress:

External ingress controller
===========================

If the cluster already has an ingress controller that terminates the external traffic, set
``EXTERNAL_INGRESS`` to its ingress class (e.g. ``traefik`` on Rancher/RKE2, or ``nginx``). Then:

* Kaapana creates two ingresses with this class for ``HOSTNAME``: ``/`` to oauth2-proxy (the login)
  and ``/auth`` to Keycloak. All other requests reach Kaapana's own Traefik through oauth2-proxy.
* TLS is terminated by the cluster's ingress controller with its certificate, e.g. the wildcard
  certificate of the platform provider (``*.<domain>``) as its default certificate. The hostname
  has to be covered by that certificate. Inside the cluster, oauth2-proxy is reached via plain HTTP.
* Traefik and oauth2-proxy are ``ClusterIP`` services instead of ``NodePort`` services on ports
  80/443; Traefik's HTTPS entrypoint listens on port 9000.

Kaapana's internal ingresses use the ingress class ``kaapana``, which only Kaapana's own Traefik
serves. This keeps the cluster's ingress controller from publishing them directly, which would
bypass the login.

.. _existing_cluster_rwo:

Storage without ReadWriteMany
=============================

Several pods share Kaapana's volumes (e.g. workflow data). With ``NO_READ_WRITE_MANY_SUPPORT=true``
the volumes are ``ReadWriteOnce``, which can only be mounted on one node at a time, so all pods using
the volumes of a namespace are scheduled on the same node:

* one pod per namespace owns the volumes and carries the label ``kaapana.io/rwo-anchor=true``:
  the Airflow scheduler (services namespace), kube-helm (admin namespace) and ``project-runtime``
  (each project namespace).
* all other pods using these volumes get a ``podAffinity`` to that pod: the services and admin
  components through their Helm charts, processing containers and Airflow worker pods when they
  are created.

While an anchor pod is not running (e.g. during a restart), new pods of its namespace stay
``Pending`` until it is back.


.. _existing_cluster_example:

Example: managed Rancher cluster
================================

.. code-block:: bash

   PLATFORM_PREFIX="myplatform"
   PREFIX_ALL_NAMESPACES=true          # myplatform-admin / -services / -extensions
   RESTRICTED_RBAC=true
   NO_READ_WRITE_MANY_SUPPORT=true
   EXTERNAL_INGRESS="traefik"
   DICOM_PORT="31112"
   STORAGE_PROVIDER="default"
   STORAGE_CLASS=""                    # empty: the cluster's default storage class

Before deploying: with restricted RBAC you can't install CRDs and can't create namespaces (no
ClusterRole), so this has to be prepared:

#. Have the cluster administrators install the Traefik CRDs.
#. Create the namespaces ``myplatform-admin``, ``myplatform-services``, ``myplatform-extensions``
   and ``myplatform-project-admin`` (e.g. in Rancher).
#. Switch to the cluster's context: ``kubectl config use-context <context>``.
#. Deploy as described in :ref:`deployment`.
