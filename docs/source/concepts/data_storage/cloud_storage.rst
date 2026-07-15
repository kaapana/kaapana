.. _concepts_cloud_storage:

Cloud Storage
################################

Kaapana's core services -- the internal PACS (dcm4chee), MinIO, and OpenSearch -- each claim a Kubernetes **PersistentVolumeClaim** rather than writing to a server's disk directly.

* **Single node.** The microk8s hostpath provisioner backs a PVC with a plain directory on that machine's disk, with no replication underneath it.
* **Multi-node.** **Longhorn** backs a PVC with a distributed, replicated block storage system, so the volume survives losing a node and stays reachable from wherever a pod lands.

Because the services only ever see a PVC, swapping the provider behind it -- from hostpath to Longhorn, or to any CSI-compatible provider on a :ref:`managed Kubernetes distribution<concepts_multi_node_architecture>` -- needs no changes to dcm4chee, MinIO, or OpenSearch themselves.

See :ref:`kaapana_storage` for how each provider is set up and which of the three storage classes to pick for databases, workflow data, and bulk image data.
