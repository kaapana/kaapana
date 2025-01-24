.. _migration_guide_0.4:

Migration from Version 0.3.5 to 0.4.1
*************************************

Version 0.4.0 introduces several breaking changes.
This guide outlines the steps required to migrate your data, including DICOM files, metadata, user data, and more, from a Kaapana instance based on 0.3.5 to 0.4.1.
Version 0.4.1 comes with some fixes, that eases the migration procedure.
Additionally, we included a section with information about :ref:`breaking changes regarding custom Airflow DAGs<migrating_airflow_dags_0.4>`.

The data migration process consists of the following steps, detailed below:

#. :ref:`Prepare the migration on the old platform (0.3.x version)<prepare_migration_0.4>`
#. :ref:`Undeploy the old platform and uninstall the MicroK8s cluster<undeploy_and_uninstall_0.4>`
#. :ref:`Migrate PostgreSQL databases<database_migration_0.4>`
#. :ref:`Install the MicroK8s cluster and deploy the new platform<install_and_deploy_0.4>`
#. :ref:`Restore metadata in OpenSearch<restore_metadata_0.4>`
#. :ref:`Migrate thumbnails and static website results<thumbnails_and_staticwebsiteresults_0.4>`
#. :ref:`Add a new realm-role in Keycloak<new_realm_role_0.4>`

Requirements:
    - Admin user login credentials.
    - Access to the Keycloak admin console.
    - Access to the Kubernetes dashboard for editing configurations and restarting pods.
    - Root permissions on the host machine where the platform is deployed.
    - Login credentials for a private registry.
    - Script ``deploy_platform_0.3.5.sh`` to undeploy old platform.
    - Script ``deploy:platform_0.4.0.sh`` to deploy the new platform.

.. _prepare_migration_0.4:

Prepare the Migration Before Undeploying the Platform
-----------------------------------------------------

Before undeploying your 0.3.x platform, complete the following steps:

1. Verify Keycloak Configuration:
    - Log in to the Keycloak admin console with your admin credentials.
    - Navigate to the Kaapana realm management.
    - In the list of users, ensure the *system* user belongs to the *kaapana_admin* group.

2. Prepare OpenSearch Meta-Information:

    .. note::

        Step 2 and 3 are only necessary, when you created additional metadata for dicom series and stored them in Opensearch.
        If not skip step 2 and 3.

    .. important::

        The following steps only work, when you deployed the current platform in development mode.
        You can put the platform into development with two steps.
        
        1. Open the ``deploy_platform_0.3.5.sh`` script and change ``DEV_MODE="false"`` to ``DEV_MODE="true"``.
        2. Then run ``./deploy_platform_0.3.5.sh`` and select action ``1) Un- and Re-deploy``
        
        Before you can continue, you have to wait until all pods are in the *Running* or *Completed* state.
        
    - Open the Kubernetes dashboard and locate the `os-config` ConfigMap in the `services` namespace.
    - Click *Edit Resource* and exchange the `opensearch.yml` file with the following:

        .. code-block:: yaml
            
            opensearch.yml: |
                ---
                cluster.name: docker-cluster
                path.repo: ["/usr/share/opensearch/logs"]
                network.host: 0.0.0.0

    - Save the ConfigMap.

    - Locate the `opensearch-de` deployment in the `services` namespace.
    - Update the following sections:
        
    - Under `spec.template.spec.volumes`, modify the `sec-config` entry:

        .. code-block:: yaml

            - name: sec-config
              configMap:
                name: os-config
                items:
                  - key: config.yml
                    path: config.yml
                  - key: opensearch.yml
                    path: opensearch.yml
                defaultMode: 420

    - Under `spec.template.spec.containers`, add the following `volumeMount` to the OpenSearch container:

        .. code-block:: yaml

            - name: sec-config
              mountPath: /usr/share/opensearch/config/opensearch.yml
              subPath: opensearch.yml

    - Save the deployment configuration. This will restart the OpenSearch pod.

    .. note::

        If errors occur in the meta-dashboard, you may need to manually restart the OpenSearch pod. 
        Delete the pod associated with the `opensearch-de` deployment using the Kubernetes dashboard, 
        but **do not** delete the deployment itself.

3. Take a Snapshot of the Metadata:
    - Open the OpenSearch index management dashboard at: ``https://<hostname>/meta/app/opensearch_index_management_dashboards#/repositories``.
    - Create a repository with type *Shared file system* and the location: ``/usr/share/opensearch/logs/snapshots``.
    - Navigate to the *Snapshots* menu, take a snapshot of the `meta-index`
    - As soon as the snapshot completed back up the snapshot files located on your server in ``${FAST_DATA_DIR}/os/logs/snapshots/`` to a secure location.

        .. code-block:: shell

            sudo cp -r --preserve `${FAST_DATA_DIR}/os/logs/snapshots/ /path/to/snapshot-backup/

.. _undeploy_and_uninstall_0.4:

Undeployment and Uninstallation
--------------------------------

To undeploy and uninstall the current platform:

1. Undeploy the Platform:
    - Use the `deploy_platform.sh` script for version 0.3.x:
    
        .. code-block:: shell

            ./deploy_platform_0.3.5.sh --quiet --undeploy

2. Uninstall the MicroK8s Cluster:
    - Download the `server_installation.sh` script for version 0.3.5:
    
        .. code-block:: shell

            curl https://raw.githubusercontent.com/kaapana/kaapana/refs/tags/0.3.5/server-installation/server_installation.sh -o server-installation-0.3.5.sh

    - Uninstall the cluster:
    
        .. code-block:: shell

            sudo ./server-installation-0.3.5.sh --uninstall

.. _database_migration_0.4:

Database Migration
------------------

Before deploying the new platform version, migrate the PostgreSQL database:


1. Download the migration script:
   
   .. code-block:: shell

      curl https://raw.githubusercontent.com/kaapana/kaapana/refs/tags/0.4.1/utils/migration_0.3.x-0.4.x.sh -o migration_0.3.x-0.4.x.sh

2. Update the following variables in the script:

    - `CONTAINER_REGISTRY_URL` - Url of the private container registry
    - `IMAGE_POSTGRES_OLD`  - Kaapana postgres image of the old platform version
    - `IMAGE_POSTGRES_NEW` - Kaapana postgres image of the new platform version
    - `IMAGE_POSTGRES_DCM4CHE_OLD` - Kaapana dcm4che image of the old platform version
    - `IMAGE_POSTGRES_DCM4CHE_NEW` - Kaapana dcm4che image of the old platform version
    - `TMP_MIGRATION_DIR` - Directory on the server, where database backups and dumps and metadata backups should be stored
    - `FAST_DATA_DIR` - Directory on the server, where stateful application-data will be stored (databases, processing tmp data etc.)

.. note::

    The provided migration script will backup all database files in ``TMP_MIGRATION_DIR``.
    It will overwrite all database directories in the ``FAST_DATA_DIR``.

3. Log in to the container registry:
   
   .. code-block:: shell

      docker login

4. Run the migration script with root permissions:
   
   .. code-block:: shell

        sudo chmod +x ./migration_0.3.x-0.4.x.sh
        sudo ./migration_0.3.x-0.4.x.sh

.. _install_and_deploy_0.4:

Install MicroK8s Cluster and Deploy New Platform Version
---------------------------------------------------------

1. Download the new installation script:
   
   .. code-block:: shell

      curl https://raw.githubusercontent.com/kaapana/kaapana/refs/tags/0.4.0/server-installation/server_installation.sh -o server-installation-0.4.0.sh

2. Install the MicroK8s cluster:
   
   .. code-block:: shell

      sudo ./server-installation-0.4.0.sh

3. Deploy the platform:

    .. note::
        As the migration script overwrote the database files in the ``FAST_DATA_DIR`` you can select the same ``FAST_DATA_DIR`` and ``SLOW_DATA_DIR`` for the new deployment as for the old deployment.

   
   .. code-block:: shell

      ./deploy_platform_0.4.0.sh

.. _restore_metadata_0.4:

Restore Metadata from Snapshot
------------------------------

In this step, we restore metadata stored in the snapshot created during the migration preparation phase. 
Follow these detailed steps to ensure the metadata is correctly restored and reindexed:

1. Copy Snapshot Files:
    - Locate the snapshot files you backed up earlier from the old platform. These files should be stored outside of the ``FAST_DATA_DIR`` or ``SLOW_DATA_DIR`` to avoid accidental deletion during the migration process.
    - Copy all snapshot files to the appropriate directory on the new platform:

        .. code-block:: bash
            
            sudo cp -r --preserve /path/to/snapshot-backup ${FAST_DATA_DIR}/os/snapshots

    - Ensure the files are placed under the directory ``${FAST_DATA_DIR}/os/snapshots``, as OpenSearch expects them in this location.

2. Restore the Snapshot in OpenSearch:
    - Open the OpenSearch dashboard in your browser by navigating to: ``https://<hostname>/meta/app/opensearch_index_management_dashboards#/repositories``.
    - Create a repository for the snapshots:
        - Click on *Create Repository* and choose the repository type *Shared file system*.
        - Set the location to ``/usr/share/snapshots`` and save the repository.
    - Navigate to the *Snapshots* section in OpenSearch.
    - Select the snapshot you created on the previous platform and click on *Restore*.
    - In the restore configuration, select the `meta-index` as the index to restore.
    - Enable the option *Add prefix to restored index names* to avoid conflicts with existing indexes. For example, this might rename the restored index to `restored_meta-index`.

3. Reindex the Restored Metadata:
    - Navigate to the *Index Management - Indexes* section in OpenSearch.
    - Select the newly restored index (e.g., `restored_meta-index`) and apply the *Reindex* action.
    - Specify the index `project_admin` as the destination index.
    - Then click on *Reindex* to begin the operation.
    - Once the reindexing operation completed, verify in the Meta-Dashboard that `project_admin` contains all the expected metadata.

.. _thumbnails_and_staticwebsiteresults_0.4:

Migrate Thumbnails and Static Website Results
---------------------------------------------

In this step, you will move the data for thumbnails and static website results to the new directory structure required by the updated platform version. 
Follow the steps below carefully to ensure a smooth migration:

1. Start a MinIO Sync Application from the Extensions page:

    - The *Host Directory* can be any accessible non-emtpy directory on your system, as its content will not directly affect the migration process.
    - The *MINIO Path* can also be arbitrary for the sync application.

2. Once the sync application is running, enter the MinIO sync pod using the Kubernetes dashboard or via the command line:

    .. code-block:: shell

        kubectl exec -it <minio-sync-pod-name> -- /bin/bash

    Replace `<minio-sync-pod-name>` with the actual name of your running MinIO sync pod.

3. Inside the MinIO sync pod, execute the following commands to move the required data to the updated directory paths:

    .. code-block:: shell

        mc find minio/thumbnails --name "*.png" -print {base} -exec "mc mv {} minio/project-admin/thumbnails/"
        mc mv -r minio/staticwebsiteresults minio/project-admin

4. After the commands completed, you can delete the minio-sync application on the *Extensions* page.

.. _new_realm_role_0.4:

Add New Realm-Role in Keycloak
------------------------------

#. Login to the Keycloak admin console and make sure the *kaapana* realm is selected in the Keycloak menu.
#. In the Keycloak Menu navigate to *Realm Roles*.
#. Click on *Create Role*, set the *Role name* to *project-manager* and click *Save*.
#. Then navigate to *Groups* and click on the group *kaapana_project_manager*.
#. Open the tab *Role mapping* and click on *Assign role*.
#. You might have to change *Filter by clients* to *Filter by realm roles*
#. Then select the role *project-manager* and click on *Assign*.

.. _migrating_airflow_dags_0.4:

Migrating Airflow DAGs
-----------------------

In Kaapana version 0.4.0, detailed in the :ref:`Release Notes v0.4.0 <release-0.4.0>`, a new feature introduces data separation for DICOM data, MinIO data, and metadata. 
This enhancement ensures that workflows and jobs are executed within a dedicated project context, restricting access to data exclusively within the respective project. 

To support this feature, processing containers have been introduced for all operators that interact with the aforementioned data storages. 
These containers enforce project-level data access restrictions for processes within operators.

If you have developed custom DAGs and want to maintain data separation, it is essential to replace any local operators with their corresponding processing container operators. 
The table below provides a mapping of local operators to their secure counterparts:

=================================== ===================================
Local operators                     Operators with processing container
=================================== ===================================
LocalDeleteFromMetaOperator         DeleteFromMetaOperator
LocalDeleteFromPacsOperator         DeleteFromPacsOperator
LocalGetInputDataOperator           GetInputOperator
LocalGetRefSeriesOperator           GetRefSeriesOperator
LocalJson2MetaOperator              Json2MetaOperator
LocalMinioOperator                  MinioOperator
=================================== ===================================

    .. warning::

        Local operators and their processing-container counterparts may have distinct arguments and configuration options, requiring careful review and adjustment during migration to ensure compatibility and proper functionality.
