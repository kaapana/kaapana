.. _migration_guide_0.7:

Migration from Version 0.6.x to 0.7.x
*************************************

In 0.7 each project is identified internally by a short, stable ``short_id`` instead of its name, and the bundled PostgreSQL is upgraded from 17 to 18.
Your projects, users and data are preserved, but **one manual step is required after the upgrade**: re-keying each project's storage to its ``short_id``.

Read this page fully before you start.

.. note::

   Migration runs during ``deploy`` when the version recorded in ``<FAST_DATA_DIR>/version`` is 0.6.x.

Before you start
================

- **Back up your data directories**, the upgrade does not back them up for you:

  .. code-block:: bash

     sudo cp -a <FAST_DATA_DIR> /path/to/backup/fast
     sudo cp -a <SLOW_DATA_DIR> /path/to/backup/slow   # skip if same as fast

- Check your current version (should read ``0.6.x``):

  .. code-block:: bash

     cat <FAST_DATA_DIR>/version

Performing the migration
========================

1. **Undeploy** the running 0.6.x platform:

   .. code-block:: bash

      ./kaapanactl.sh deploy --undeploy

2. **Deploy 0.7.x.** Migration runs automatically after you confirm the prompt.
   See :ref:`deployment` for the full deploy command.

   .. code-block:: bash

      ./kaapanactl.sh deploy ...

   During migration

   * the bundled PostgreSQL is upgraded in place (17 → 18, the previous cluster is kept alongside as ``<cluster>_pg17_bak``)
   * the admin project's namespace and workflow volumes are moved to their new prefixed name
   * no Keycloak admin password is required (see `Keycloak`_ below).

3. **Wait** until the platform is fully up:

   .. code-block:: bash

      kubectl get pods -A | grep -vE 'Running|Completed'   # should be empty for the namespaces of the latest deployed platform

4. **Re-key project storage (required).** Before you do anything else with the platform, run the re-key script. 
   This moves each project's MinIO bucket and OpenSearch index from its name to its ``short_id``. 
   Run it once, with the platform up. It is idempotent (safe to re-run) , and skips the admin project (whose ``short_id`` is unchanged).
   The access-information-interface container has a read-only filesystem, so the script is piped in on stdin rather than copied:

   .. code-block:: bash

      NS=<SERVICES_NAMESPACE>   # usually "services"
      POD=$(kubectl get pods -n $NS -l app.kubernetes.io/name=access-information-interface -o name | head -1)
      kubectl exec -i -n $NS "$POD" -c access-information-interface \
        -- sh -c 'cd /app && python3 -' < utils/migration-chart/docker/files/rekey_projects.py

   Watch for ``Project re-key finished``; each project logs the number of objects copied and the alias created.

   .. warning::

      Do not ingest new data into a project until its re-key has finished.

5. **Verify:** each project shows its images, metadata and thumbnails in the UI, and users can log in and see their projects.

What changes in 0.7.0
=====================

Project identifier: name → short_id
-----------------------------------

A project's ``short_id`` is the first 8 characters of its UUID (the admin project keeps the literal ``admin``). 
You can find each project's ``short_id`` under **System → Projects** in the UI. 
Every project-scoped datastore is keyed by it:

.. list-table::
   :header-rows: 1

   * - Datastore
     - 0.6.x (by name)
     - 0.7.x (by short_id)
   * - Kubernetes namespace
     - ``project-<name>``
     - ``<platform_prefix>-project-<short_id>``
   * - MinIO bucket
     - ``project-<name>``
     - ``project-<short_id>``
   * - OpenSearch index
     - ``project_<name>``
     - ``project_<short_id>``
   * - DICOM AE title
     - ``kp-<name>``
     - ``kp-<short_id>``
   * - DICOM tag (0012,0020)
     - ``<name>``
     - ``<short_id>``

Namespaces and buckets/indexes are handled by the migration and the re-key step above. 
If you push from an **external** DICOM node, update its called-AE title from ``kp-<name>`` to ``kp-<short_id>``.

Keycloak
--------

Your Keycloak realm, users and groups are preserved. 
From 0.7.0, services authenticate through dedicated clients instead of the admin password (see :ref:`service_to_service_auth`). 
These clients are created **automatically** during the migration deployment.

The admin password is (re)set on each deploy and printed at the end. 
You can change it later through the Keycloak UI or with ``./kaapanactl.sh set-keycloak-admin-password``.
See :ref:`Keycloak admin password <keycloak_admin_password>`.

Access rights
-------------

Several permission names changed in 0.7 (for example ``manage_project_users`` → ``manage_users``), and the multi-installable-extension permission was split into separate application permissions. 
Default roles are updated automatically on startup. 
Custom roles keep their existing access, but do not gain the new application permissions automatically.
Add those under **System → Roles** if needed.

Troubleshooting
===============

- **A project's datasets look empty after the upgrade:** the re-key step (step 4) has not run yet, or did not finish. Re-run it, it is idempotent.

- **A pod does not come up:** ``kubectl get pods -A | grep -vE 'Running|Completed'``, then ``kubectl logs -n <ns> <pod> --previous``. The access-information-interface pod applies the rights update on startup and is the usual first place to look.

- **Roll back:** restore the backup taken in `Before you start`_ and redeploy 0.6.x.
