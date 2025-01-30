.. _faq_change_containerd_location:

================================================
How to change containerd storage location       
================================================

Why change the storage location of containerd?
----------------------------------------------
In some installations, the default location `/var/lib/containerd/` may not have enough disk space to store all containers. If another location has more available space, you can reconfigure containerd to use that location.

Changing the storage location in MicroK8s
------------------------------------------
In MicroK8s, container data is stored under:

- `/var/snap/microk8s/common/var/lib/containerd`
- `/var/snap/microk8s/common/run/`

You can run `df -h` to see if the filesystem holding those paths is running low.

To move the storage to a different volume (e.g., `/dev/sdc` mounted at `/mnt`), follow these steps:

1. Edit the containerd configuration file:

   ```bash
   sudo nano /var/snap/microk8s/current/args/containerd
   ```

2. Modify the `--root` and `--state` parameters to point to the new storage location:

   ```
   --config ${SNAP_DATA}/args/containerd.toml
   --root /mnt/var/lib/containerd
   --state /mnt/run/containerd
   --address ${SNAP_COMMON}/run/containerd.sock
   ```

3. Save the file and restart MicroK8s:

   ```bash
   microk8s.stop
   microk8s.start
   ```

Alternative: Using a Persistent Volume
---------------------------------------
For a single-node MicroK8s setup, an alternative is specifying a host path in the Persistent Volume (PV) YAML definition. This allows pods to store data in a specified location directly:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: my-volume
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: manual
  hostPath:
    path: "/mnt/k8s-storage"
```

Further Reading
---------------
- [MicroK8s Storage Documentation](https://microk8s.io/docs)
- [Containerd Configuration Reference](https://containerd.io/docs/)
