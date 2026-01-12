.. _kaapana_storage:


Storage Provisioners
********************


Kaapana supports two types of provisioners for persistent storage in Kubernetes:


- **microk8s Hostpath Storage**: Default solution for single-node clusters
- **Longhorn**: Required distributed storage solution for multi-node clusters


Choose the appropriate provisioner based on your deployment architecture.



Microk8s Hostpath Storage
=========================


Overview
--------


Hostpath storage is the default provisioner for single-node Kaapana deployments. This provisioner automatically creates PersistentVolumes from PersistentVolumeClaims, backed by host filesystem paths on the local node.


This is suitable only for single-node environments where all data resides on one machine. For multi-node deployments, use Longhorn instead (see :ref:`longhorn_storage`).


Installation
------------


The hostpath provisioner is automatically installed during the standard Kaapana server installation. No additional configuration steps are required to use it.


PersistentVolumeClaims created during Kaapana deployment will be automatically provisioned using hostpath storage.



.. _longhorn_storage:


Longhorn Distributed Storage
=============================


.. attention::


   To deploy Kaapana in a multi-node cluster, you **must** use a distributed storage solution. Longhorn provides reliable distributed block storage compatible with Kubernetes and is the recommended solution for multi-node Kaapana deployments.


Overview
--------


Longhorn is a lightweight, reliable distributed block storage system for Kubernetes. It ensures that data is consistently available across all nodes in your cluster, allowing pods to be scheduled on any node while maintaining access to their persistent volumes.


Installation Prerequisites
---------------------------


Before installing Longhorn, verify the following on each node:


- microk8s is installed and the multi-node cluster is configured (see :ref:`multi_node`)
- The cluster is stable and all nodes report as ``Ready``
- Sufficient free disk space is available on each node for storage


Installation Steps
------------------


1. **Install Longhorn via Helm on Every Node**


   Add the Longhorn Helm repository and install Longhorn in the ``longhorn-system`` namespace:


   .. code-block:: bash


      helm repo add longhorn https://charts.longhorn.io
      helm repo update
      helm install longhorn longhorn/longhorn \
        --namespace longhorn-system \
        --create-namespace \
        --version 1.10.1 \
        --set csi.kubeletRootDir="/var/snap/microk8s/common/var/lib/kubelet"


   .. note::


      This command is tested with Longhorn version 1.10.1. For the latest version, replace ``1.10.1`` with your desired version number. Refer to the `Longhorn Helm installation documentation <https://longhorn.io/docs/1.10.1/deploy/install/install-with-helm/>`_ for additional configuration options and prerequisites.


2. **Configure NO_PROXY Environment Variable**


   After installation, add Longhorn services to the ``no_proxy`` and ``NO_PROXY`` environment variables on each node to prevent proxy-related connectivity issues.


   Edit ``/etc/environment`` and add the following entries:


   .. code-block:: bash


      no_proxy="*.svc,*.cluster.local"
      NO_PROXY="*.svc,*.cluster.local"


   Then reboot each node:


   .. code-block:: bash


      sudo reboot


3. **Verify Longhorn Installation**


   Wait for all Longhorn pods to reach ``Running`` status:


   .. code-block:: bash


      kubectl get pods -n longhorn-system -o wide


   Once all pods are running, verify that Longhorn is ready:


   .. code-block:: bash


      kubectl get storageclass


   You should see a ``longhorn`` storage class listed.


Accessing the Longhorn Dashboard
---------------------------------


The Longhorn UI is accessible via ``https://<Kaapana-FQDN>/longhorn/`` after Kaapana is deployed. To enable this, configure the Ingress and middleware settings below.


**Create the Traefik Middleware and Ingress** (apply after Kaapana deployment):


.. code-block:: yaml


   apiVersion: traefik.containo.us/v1alpha1
   kind: Middleware
   metadata:
     name: strip-prefix-longhorn
     namespace: longhorn-system
   spec:
     stripPrefix:
       prefixes:
         - /longhorn


   ---
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: longhorn-ui-ingress
     namespace: longhorn-system
     annotations:
       traefik.ingress.kubernetes.io/router.entrypoints: websecure
       traefik.ingress.kubernetes.io/router.middlewares: longhorn-system-strip-prefix-longhorn@kubernetescrd
       traefik.ingress.kubernetes.io/rewrite-target: /
   spec:
     rules:
       - http:
           paths:
             - path: /longhorn
               pathType: Prefix
               backend:
                 service:
                   name: longhorn-frontend
                   port:
                     number: 80


Save this configuration to a file (e.g., ``longhorn-ingress.yaml``) and apply it:


.. code-block:: bash


   kubectl apply -f longhorn-ingress.yaml


Deploying Kaapana with Longhorn
--------------------------------


After Longhorn is installed and running on all nodes, configure the Kaapana deployment to use Longhorn as the storage provider.


Edit the deployment script (see :ref:`deployment`) and locate the ``load_kaapana_config()`` function. In the **Storage** configuration section, update:


.. code-block:: bash

   ######################################################
   # Storage
   ######################################################
   STORAGE_PROVIDER="longhorn"  # Changed from "hostpath" to "longhorn"
   VOLUME_SLOW_DATA="100Gi"     # Set to your expected slow data directory size
                                # Examples: 100Gi, 500Gi, 1Ti, etc.


.. warning::


   Longhorn volumes have size limits. The ``VOLUME_SLOW_DATA`` setting defines the maximum size of the slow data persistent volume. You can extend volumes later via the Longhorn dashboard if needed. Refer to the `Longhorn documentation Volume Expansion <https://longhorn.io/docs/1.10.1/nodes-and-volumes/volumes/expansion/>`_ for volume extension instructions.


After updating the configuration, deploy Kaapana on the main node as usual (see :ref:`installation_guide`).


Verifying the Deployment
-------------------------


After deployment completes, verify that Kaapana pods are distributed across multiple nodes and using Longhorn storage:


.. code-block:: bash


   # Check pod distribution across nodes
   kubectl get pods -A -o wide


   # Verify Longhorn volumes are in use
   kubectl get pvc -A


All pods should show different nodes in the ``NODE`` column for a properly balanced multi-node deployment.


Troubleshooting
---------------


If pods are not scheduling or Longhorn volumes are not attaching, refer to:


- `Longhorn Troubleshooting Documentation <https://longhorn.io/docs/1.10.1/troubleshooting/>`_
- Longhorn dashboard: ``https://<Kaapana-FQDN>/longhorn/`` (after Ingress is configured)
- Node and volume logs: ``kubectl logs -n longhorn-system -l app=longhorn-manager``


Kaapana Storage Classes
=======================


Kaapana uses three predefined storage class categories for persistent storage:

- **STORAGE_CLASS_SLOW**: For large volumes with slower access patterns (medical imaging data)
- **STORAGE_CLASS_FAST**: For high-performance storage (e.g. databases)
- **STORAGE_CLASS_WORKFLOW**: For workflow execution and temporary data

The ``STORAGE_PROVIDER`` setting in the deployment script sets the defaults for these three storage class kinds. Depending on the selected provisioner, Kaapana automatically assigns the appropriate storage classes. You can also manually override these settings for advanced configurations (see :ref:`advanced_storage_config`).


Hostpath Storage Classes
------------------------


When using the **microk8s hostpath provisioner**, Kaapana uses the following storage classes:


.. list-table:: Hostpath Storage Classes
   :header-rows: 1
   :widths: 35 65


   * - Storage Class
     - Purpose
   * - ``kaapana-hostpath-slow-data-dir``
     - Mapping to Kaapana ``SLOW_DATA_DIR``, suitable for medical imaging data storage
   * - ``kaapana-hostpath-fast-data-dir``
     - Mapping to Kaapana ``FAST_DATA_DIR``, fast local storage for databases and workflow execution


For hostpath provisioner, the only difference between storage classes is their storage location. Both use local hostpath directories as their backing storage. This approach is suitable only for single-node deployments where all data resides on one machine.


Longhorn Storage Classes
------------------------


When using **Longhorn** as the storage provisioner, Kaapana uses three distinct storage classes with different scheduling and access patterns:


.. list-table:: Longhorn Storage Classes
   :header-rows: 1
   :widths: 30 45 25


   * - Storage Class
     - Purpose
     - Scheduling
   * - ``kaapana-longhorn-slow-data``
     - Large volumes for medical imaging data with slower access patterns
     - Main node only
   * - ``kaapana-longhorn-fast-db``
     - Fast database volumes requiring high performance
     - Main node only
   * - ``kaapana-longhorn-fast-workflow``
     - Workflow execution and temporary data
     - Distributed across all nodes



**Important Characteristics:**


The PersistentVolumeClaims backed by the ``*-slow`` and ``*-fast`` storage classes are provisioned on the main node only. This means all pods mounting these volumes are constrained to run on the primary node. This design pattern ensures:


- **Fast access** to frequently accessed data (databases, large imaging volumes)
- **Data locality** to minimize network overhead
- **Simplified management** of performance-critical components


In contrast, the PVC backed by the ``*-workflow`` storage class uses shared volumes distributed across all nodes, enabling workflow pods to be scheduled flexibly across the cluster while maintaining access to shared data.


.. seealso::


   For detailed deployment configuration options regarding ``fast_data_dir`` and ``slow_data_dir``, refer to the :ref:`deployment` guide.


Storage Configuration
~~~~~~~~~~~~~~~~~~~~~


The storage classes are automatically configured based on the ``STORAGE_PROVIDER`` setting in the deployment script. Ensure you select the correct provisioner for your deployment architecture:


- **Single-node deployments**: Use ``STORAGE_PROVIDER="hostpath"``
- **Multi-node deployments**: Use ``STORAGE_PROVIDER="longhorn"``


.. _advanced_storage_config:


Advanced Storage Configuration
==============================


Mixed Storage Solutions
-----------------------


Kaapana's deployment script supports advanced configurations that allow you to mix different storage provisioners within a single cluster. This flexibility enables you to optimize storage performance and resilience based on your specific requirements.

For example, you can configure:

- **Slow data storage** backed by a network filesystem (NFS) volume using hostpath provisioner
- **Fast database and workflow storage** using Longhorn for high performance and redundancy

To implement this mixed storage approach, edit the deployment script and manually override specific storage classes. This can be achieved by selecting your main storage provider (e.g., "longhorn") and then overriding individual storage class variables at the end of the ``setup_storage_provider`` function:

.. code-block:: bash

   # In the setup_storage_provider function, after the case statement
   # Add manual overrides for mixed storage configuration:
   STORAGE_CLASS_SLOW="kaapana-hostpath-slow-data-dir"      # e.g. backed by an NFS disk setup for SLOW_DATA_DIR

This configuration allows you to leverage the benefits of both storage solutions:

- **Hostpath (with NFS)**: Cost-effective storage for large medical imaging data, if setup on a NFS drive, with external backup support
- **Longhorn**: High-performance, replicated storage for critical databases and workflow data with built-in backup capabilities

Longhorn Backups in Single-Node Clusters
-----------------------------------------

While Longhorn is typically recommended for multi-node deployments, it can also be beneficial in single-node clusters. Longhorn provides powerful backup and disaster recovery features.

For detailed information on Longhorn backups and snapshot management, refer to the `Longhorn Backup and Restore documentation <https://longhorn.io/docs/1.10.1/snapshots-and-backups/backup-and-restore/>`_.
