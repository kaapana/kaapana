.. _concepts_cloud_storage:

Cloud Storage
################################

Kaapana's core services -- the internal PACS (dcm4chee), MinIO, and OpenSearch -- do not write directly to a server's disk. Kubernetes sits in between: every one of these services claims a **PersistentVolumeClaim**, and a storage provider decides what actually backs it.

Kaapana is tested with some default storage providers, but you can also configure your own. The default providers are:

* **Single node.** The microk8s hostpath provisioner backs a PVC with a plain directory on that one machine's disk -- it simulates a Kubernetes-managed volume, but there is no replication or distribution underneath it.
* **Multi-node.** **Longhorn** backs a PVC with a real distributed block storage system, replicated across nodes, so the volume stays reachable regardless of which node a pod lands on.

See :ref:`kaapana_storage` for how each is set up and the three storage classes used for databases, workflow data, and bulk image data.

