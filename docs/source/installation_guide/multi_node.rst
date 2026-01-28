.. _multi_node:

Multi-Node Deployment
*********************

Kaapana supports multi-node deployments using microk8s Kubernetes clusters. This guide walks you through the necessary steps to set up a multi-node environment.

Prerequisites
=============

Before deploying Kaapana across multiple nodes, ensure you have:

- Multiple physical or virtual machines that will serve as Kubernetes nodes
- Network connectivity between all nodes
- Administrative access to all machines

Setting Up Your Multi-Node Kubernetes Cluster
==============================================

1. **Install microk8s on Each Node**

   Run the :ref:`server_installation` steps on each machine to install microk8s.

2. **Create a Multi-Node Cluster**

   Follow the official microk8s clustering documentation to join nodes together:

   https://microk8s.io/docs/clustering

   Key steps include:

   - Initialize the primary node
   - Generate join tokens on the primary node
   - Join additional nodes to the cluster

3. **Verify Cluster Setup**

   Confirm that all nodes are part of the cluster:

   .. code-block:: bash

      microk8s kubectl get nodes

   All nodes should appear in the output with a ``Ready`` status.

4. **Validate Network Configuration**

   Ensure that:

   - All nodes can communicate with each other
   - Network policies allow pod-to-pod communication across nodes
   - DNS resolution works between nodes

Configuring Distributed Storage
================================

For multi-node deployments, you must set up a distributed storage solution compatible with Kubernetes. Kaapana supports Longhorn for this purpose.

.. seealso::

   Refer to the :ref:`kaapana_storage` guide for detailed installation instructions on setting up Longhorn across your cluster.

Deploying Kaapana on the Multi-Node Cluster
============================================

Once your multi-node Kubernetes cluster is ready and distributed storage is configured, proceed with the standard Kaapana installation instructions using the main node as your deployment point. 

Configure the deployment to use the distributed storage provider (see :ref:`kaapana_storage`) to ensure that Kaapana pods can be scheduled across different nodes.

Verifying Multi-Node Pod Distribution
======================================

After deployment, verify that Kaapana pods are distributed across different nodes:

.. code-block:: bash

   kubectl get pods -A -o wide

The ``NODE`` column shows which node each pod is running on. A healthy multi-node deployment should show pods scheduled across multiple nodes.
