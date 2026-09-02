.. _faq_recover_data_after_reinstall:

##########################################################
How to recover platform data after the cluster was lost
##########################################################

The platform keeps every persistent volume in a directory
``<data dir>/<namespace>-<claim>-pvc-<uuid>`` under ``fast_data_dir`` or ``slow_data_dir``.
Those directories survive an OS reinstall (when the data directories live on separate storage),
a ``kaapanactl.sh install --uninstall`` and deleted PVCs - but the cluster no longer knows about
them, and a plain deploy provisions **empty** volumes next to the old data.

``utils/recover_data.sh`` reattaches the surviving directories. It recreates the namespaces and
claims with the Helm ownership the deploy expects and binds each claim to a hand-made
PersistentVolume that points at its directory. Nothing on disk is moved or deleted, and no image
or StorageClass is needed.

*********
Procedure
*********

#. Install the server as usual (``kaapanactl.sh install``), so that MicroK8s is running and
   empty. Do **not** deploy yet.
#. Run the recovery with the data directories, the platform prefix and - for a distribution
   that renames the admin chart - the admin release name of the previous deployment::

       ./utils/recover_data.sh --fast-dir /home/kaapana --slow-dir /home/kaapana \
           --platform-prefix kaapana --dry-run
       ./utils/recover_data.sh --fast-dir /home/kaapana --slow-dir /home/kaapana \
           --platform-prefix kaapana

   ``--dry-run`` prints the manifests instead of applying them. For data of a 0.6.x deployment,
   whose project namespaces have no prefix, pass ``--no-prefix`` instead of ``--platform-prefix``.
   See ``--help`` for the namespace, release name, ``--volume-slow-data`` and ``--node`` options.
#. Deploy the platform as usual. Helm adopts the recovered namespaces and claims, so the
   project data, the Keycloak database and the TLS state come back.

The script refuses to run while the platform is deployed (Helm releases in the admin release
namespaces); the storage class and GPU operator releases may stay. Directories of claims it
does not know - extension applications, which belong to their own Helm release - are listed and
left in place. To recover those too, pass ``--claims-file`` with one line per claim::

    # <namespace>/<claim>  <class: fast|slow>  <size>  <release>  <release namespace>
    services/my-extension-data-pv-claim  fast  1Gi  my-extension  admin

The release is the chart name for extensions that are installed once (preinstalled or from the
store); per-project or per-user apps get a generated release name and cannot be recovered this
way. A distribution can generate the file from its charts at build time.
