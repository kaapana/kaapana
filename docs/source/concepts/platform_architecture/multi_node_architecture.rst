.. _concepts_multi_node_architecture:

Multi-Node Architecture
##########################

A single-node Kaapana instance runs everything -- Airflow workers, GPU workflows, PACS, MinIO -- on one machine.
That is enough for development and small deployments, but it caps the platform at whatever CPU, RAM and GPUs that one machine has.
Multi-node support exists so that a Kaapana administrator can add capacity by adding nodes -- for example, routing GPU-heavy workflows like *TotalSegmentator* to a dedicated GPU node -- instead of being limited to a single box.

How scheduling and storage adapt to more than one node
==========================================================

Kubernetes itself already schedules pods across whichever nodes are part of the cluster; what changes between a single-node and a multi-node Kaapana are the two things that a single-node setup could get away with simplifying:

* **Where tasks run.** Airflow's own admission control (see :ref:`concepts_monitoring_and_resources`) tracks available CPU/RAM/GPU headroom across the cluster before Kubernetes ever schedules a task pod, so GPU workflows land on GPU-equipped nodes rather than wherever happened to be free.
* **Where data lives.** A single node can use simple ``hostPath`` volumes, because "the node" and "the cluster" are the same machine. Once there is more than one node, storage has to be reachable from whichever node a pod lands on. Kaapana uses **Longhorn** as the distributed storage backend for this case, alongside the microk8s hostpath provisioner used for single-node installs -- see :ref:`kaapana_storage` for how each is set up and which storage class to pick for databases, workflow data, and bulk image data.

This page explains why task scheduling and data storage need to change between single-node and multi-node setups. For the steps to join microk8s nodes into a cluster and roll out Longhorn, see the :ref:`Multi-Node Deployment guide<multi_node>`.

.. note::
   GPU scheduling *within* a node -- letting several tasks share one physical GPU by memory rather than by whole-device allocation -- is a separate concern from multi-node scheduling *across* nodes. See :ref:`concepts_gpu_sharing` for that mechanism.

Future Direction
================

Multi-node deployments are supported and tested on microk8s clusters, and also tested and running on Rancher. Running Kaapana on other Kubernetes distributions (AWS EKS, GCP GKE, Azure AKS, K3s, ...) is theoretically possible -- nothing in the architecture is microk8s-specific beyond the gap below -- but is not tested.

The remaining gap for full portability across distributions is:

* **Load balancing.** Bare-metal/microk8s deployments reach the platform through a ``NodePort``; cloud clusters generally expect a ``LoadBalancer`` service instead. The plan is to make the front-door service's type Helm-templated, defaulting to ``NodePort`` on bare metal and ``LoadBalancer`` elsewhere (a bare-metal ``LoadBalancer`` option such as MetalLB will be documented).

See :ref:`Multi-Node Deployment guide<multi_node>` for the current state of multi-node support and the steps to join microk8s nodes into a cluster and roll out Longhorn.
