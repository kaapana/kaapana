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
   PREFIX_ALL_NAMESPACES=true


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
   * - ``DICOM_PORT`` /
       ``global.dicom_port``
     - ``11112``
     - The DICOM receiver is exposed as a ``NodePort``. microk8s allows 11112; standard Kubernetes
       only allows node ports in 30000-32767 (e.g. ``31112``). ``0`` disables the NodePort. On
       clusters other than microk8s every node forwards the port (``externalTrafficPolicy:
       Cluster``), so DICOM can be sent to ``HOSTNAME:DICOM_PORT``.
