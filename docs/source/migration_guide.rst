.. _migration_guide:


###############
Migration Guide
###############



.. _migration_guide_0.4:


Upgrade from 0.3.x to 0.4.x
****************************

Version 0.4.0 comes with several breaking changes.
This guide will lead you through all the steps you have to take to migrate your data like dicom, metadata, userdata and more from a kaapana instance based on 0.3.x to 0.4.1.
The migration consists of the following steps that will be explained in more details below

#. :ref:`Prepare migration on the old the platform with version 0.3.x<prepare_migration_0.4>`
#. :ref:`Undeploy the old platform and uninstall the microk8s cluster<undeploy_and_uninstall_0.4>`
#. :ref:`Migrate postgres databases<database_migration_0.4>`
#. :ref:`Install the microk8s cluster and deploy the new platform version<install_and_deploy_0.4>`
#. :ref:`Restore the metadata in opensearch<restore_metadata_0.4>`
#. :ref:`Migrate thumbnails and staticwebsiteresults<thumbnails_and_staticwebsiteresults_0.4>`
#. :ref:`Add a new realm-role in Keycloak<new_realm_role_0.4>`



**Requirements:**

* Login credentials for an admin user.
* Credentials for the Keycloak admin console.
* Access to the Kubernetes dashboard in order to change configuration files and restart pods.
* Root permissions on the host machine, where the platform is deployed.
* Login credentials for a private registry.




.. _prepare_migration_0.4:

Prepare the migration before you undeploy your platform
-----------------------------------------------------------
Before you undeploy your platform based on 0.3.x you have to prepare the migration.

First, login to the Keycloak admin console with the Keycloak admin credentials.
Then, make sure you are in the kaapana realm management.
Here, navigate to the list of users, select the *system* user and make sure he is part of the group *kaapana_admin*.

As the next step we have to prepare the migration of meta-information stored in the opensearch index *meta-index*.

1. Open the Kubernetes dashboard. Find the configmap *os-config* in the *services* namespace. 
Click on the pencil to *Edit resource*.
Change the content of ``opensearch.yml`` to

    :: 

        --- 
        cluster.name: docker-cluster     
        path.repo: ["/usr/share/opensearch/logs"] 
        network.host: 0.0.0.0

*Update* the configmap.

2. Still in the Kubernetes dashboard find the deployment *opensearch-de* in the *services* namespace.
Again click the pencil in order to edit it.
Under ``spec.template.spec.volumes`` adapt the ``sec-config`` entry as follows:

    ::

        - name: sec-config
            configMap:
            name: os-config
            items:
                - key: config.yml
                path: config.yml
                - key: opensearch.yml
                path: opensearch.yml
            defaultMode: 420

Under ``spec.template.spec.containers`` add the following volumeMount to the opensearch container:

    ::

        - name: sec-config
            mountPath: /usr/share/opensearch/config/opensearch.yml
            subPath: opensearch.yml

Then click on *Update*.
This will restart the opensearch pod with the new configuration.

    .. note::
        If the meta-dashboard shows errors in the following steps you might have to restart opensearch by deleting the **pod**.
        To do so find the **pod** for the opensearch deployment and apply the action *Delete*.
        **Do not** delete the deployment!


3. Navigate to the *https://<hostname>/meta/app/opensearch_index_management_dashboards#/repositories*.
Create a repository with type *Shared  file system* and the location ``/usr/share/opensearch/logs/snapshots``.
In the opensearch menu navigate to *Snapshots* and take a snapshot of the index *meta-index*:
Click on *Take snapshot*, set a snapshot name like *meta03*, select the *meta-index* as source index and select the repository you just created.
Then click on *Add*.

4. The snapshot is stored on the host machine in ``${SLOW_DATA_DIR}/os/logs/snapshots/``.
Backup these files in a directory that is not a subpath of ``FAST_DATA_DIR`` or ``SLOW_DATA_DIR``.

We will need this snapshot later, after we deployed the new platform version.

.. _undeploy_and_uninstall_0.4:

Undeployment and uninstallation
--------------------------------
Now it is time to undeploy the current deployment and uninstall the server.
You need the ``deploy_platform.sh`` script for the currently deployed version.
We will assume you have this script and its name ``deploy_platform_0.3.x.sh``.
To undeploy the platform just run ``./deploy_platform_0.3.x.sh --quiet --undeploy``.

You also need the ``server_installation.sh`` script for platform version 0.3.x.
You can download the script by executing

    ::

        curl https://raw.githubusercontent.com/kaapana/kaapana/refs/tags/0.3.5/server-installation/server_installation.sh -o server-installation-0.3.5.sh

Then uninstall the microk8s cluster via ``sudo ./server_installation_0.3.5.sh --uninstall``

.. _database_migration_0.4:

Database migration
----------------------
Before we can deploy the new platform version we have to migrate the postgres database and remove some old files.
We provided a migration script that automates this process.
You can download it via

    ::

        curl https://raw.githubusercontent.com/kaapana/kaapana/refs/tags/0.4.1/utils/migration_0.3.x-0.4.x.sh -o migration_0.3.x-0.4.x.sh

Open the script and adapt the following variables to your scenario

    ::

        CONTAINER_REGISTRY_URL
        IMAGE_POSTGRES_OLD
        IMAGE_POSTGRES_NEW
        IMAGE_POSTGRES_DCM4CHE_OLD
        IMAGE_POSTGRES_DCM4CHE_NEW

Login to the container registry via ``docker login``.

Execute the migration script with root permissions:
    ::
        
        sudo ./migration_0.3.x-0.4.x.sh

.. _install_and_deploy_0.4:

Install microk8s cluster and deploy new platform version
----------------------------------------------------------
Now we cann install the microk8s cluster for the new platform version.
You can the server installation script via

    ::

        curl https://raw.githubusercontent.com/kaapana/kaapana/refs/tags/0.4.0/server-installation/server_installation.sh -o server-installation-0.4.0.sh
        sudo ./server_installation_0.4.0.sh

Finally deploy the platform 
    ::

        ./deploy_platform_0.4.0.sh

.. _restore_metadata_0.4:

Restore old metadata from snapshot
-----------------------------------
Now we can restore the metadata that we stored in a snapshot during one of the previous steps.
First copy  all files from the backed up snapshot into ``${SLOW_DATA_DIR}/os/snapshots``
Then navigate to *https://<hostname>/meta/app/opensearch_index_management_dashboards#/repositories* in your browser.
Create a repository with type *Shared file system* and the location ``/usr/share/snapshots``.
In the opensearch menu navigate to *Snapshots*.
Select the snapshot you created on your previous platform version and click on *Restore*.
Select *meta-index* as the index you want to restore and the option *Add prefix to restored index names*.
Next navigate to *Index Management - Indexes* and select *restored_meta-index* and apply the action *Reindex*.
As destination click on *Create Index* and set the *Index name* to *project_merged*. 
Then click on *Create* and afterwards on *Reindex*.
Wait for the reindexing operation to suceed and check in the dashboard, that *project_merged* contains all the expected metadata.
Eventually select in the *Index Managament - Indexes* the index *project_merged* and reindex it to the *project_admin* index.


.. _thumbnails_and_staticwebsiteresults_0.4:

Migrate thumbnails and staticwebsiteresults
---------------------------------------------
Data for the static website viewer and thumbnails are now expected at different paths in MinIO.
As soon as kaapana is running with the new version you can simply move this data to its correct place.
Just follow the steps below:

1. Start a minio-sync application.
Which *Host Directoy* you choose does not matter is irrelevant, as long as it is not empty. 
The *MINIO Path* can also be arbitrary.
2. Enter into the container via the Kubernetes dashboard or ``kubectl``.
3. Inside the container execute 

    ::

        mc find minio/thumbnails --name "*.png" -print {base} -exec "mc mv {} minio/project-admin/thumbnails/"
        mc mv -r minio/staticwebsiteresults minio/project-admin

.. _new_realm_role_0.4:

New realm-role in Keycloak
------------------------------
You have to add a new realm-role *project-manager* to the kaapana realm in Keycloak
Then map the group *kaapana_project_manager* to the role *project-manager*.