.. _migration_guide_0.2:

Migration from Version v0.1.3 to v0.2.2
***************************************

Follow these steps if Kaapana in Version 0.1.3 is currently running on the server and there is data on the platform which should be migrated to the new version. 
Beware that Kaapana is not a storage solution but an analysis platform, a backup of all data send to Kaapana is strongly advised. 
The platform does not provide any guarantees regarding data integrity especially if the migration between version fails. 
In such a case it would be needed to start with a fresh Kaapana installation and resend all the data. 
With these words of caution here the necessary steps:

What this migration guide presevers
-----------------------------------
- Images in PACS
- Minio Storage

Requirements
------------
* Script ``deploy_platform_0.2.2.sh`` to deploy new Kaapana version.


Instructions
------------

#. Copy the `server_installation_0.2.2.sh <https://codebase.helmholtz.cloud/kaapana/kaapana/-/raw/0.2.2/server-installation/server_installation.sh?ref_type=tags&inline=false>`_ as well as the ``deploy_platform_0.2.2.sh`` onto the server.
#. :ref:`Undeploy the old platform<deployment>` using the old ``install_platform.sh`` script by executing it and choosing option ``2) Uninstall``.

    .. image:: https://codebase.helmholtz.cloud/-/project/2521/uploads/8e2116c651e01efd555b589d5aee1df7/image.png
        :width: 148 
        :height: 40


#. When the platform is undeployed uninstall the older server initialization using the old server_installation.sh script by executing: ``sudo ./server_installation.sh --uninstall``
#. Reboot the machine
#. Follow the :ref:`Server Installation Guide<server_installation>` to initialize the server. (The ``server_installation.sh`` is the provided ``server_installation_0.2.2.sh``)
#. Add the container registry username and password in the according Line 15 & 16 in the ``deploy_platform_0.2.2.sh`` script.
#. Move data from the old installation to a temporary folder by executing ``mv /home/kaapana /home/kaapana_0.1.3``. Make sure that the directories for the new version (e.g. default ``/home/kaapana``) does not exist when the new version of the platform is booted up for the first time, so that the new platform does not boot using the old data (which would fail and leave an invalid state).
#. Follow the :ref:`Platform Deployment Guide<deployment>` using the ``deploy_platform_0.2.2.sh`` script with the preconfigured private registry.
#. Optional: If TLS certificates are installed reinstall them in the updated instance :ref:`by following the FAQ in the KAAPANA<how_to_install_tls_certificates>`
#. After the new version of the platform is successfully deployed with the initial file structure created in the fresh data directory the platform must be undeployed again by using the ``deploy_plaform_0.2.2.sh`` script and choosing option ``2) Undeploy``. Wait till the platform is undeployed.
#. Move the data from PACS and MINIO from the old installation over to the new installation be executing the following commands (if the data directories have been customized in the previous installation replace ``/home/kaapana_0.1.3`` with the path of the old installation and ``/home/kaapana`` with the path for the new installation):

    .. code-block:: shell

        sudo rm -rf /home/kaapana/dcm4che
        sudo rm -rf /home/kaapana/postgres-dcm4che
        sudo rm -rf /home/kaapana/minio
        sudo cp -r /home/kaapana_0.1.3/dcm4che /home/kaapana/dcm4che
        sudo cp -r /home/kaapana_0.1.3/postgres-dcm4che /home/kaapana/postgres-dcm4che
        sudo cp -r /home/kaapana_0.1.3/minio /home/kaapana/minio

#. Ensure that the permissions for dcm4chee are correct by executing ``sudo chown -R 1023:1023 /home/kaapana/dcm4che/server_data/``
#. Deploy the Platform again as done in step 8
#. Login to the platform and check that Store > Minio lists the files from the previous installation and that Store > OHIF shows the studies of the old version of the platform.
#. To populate the ``meta-index`` which is used by the Workflows > Datasets View as well as by all Dashboards under Meta, go to System > Airflow and click the play Button next to the ``service-re-index-dicom-data`` DAG. In the Popup menu select the “Trigger DAG” Option.
#. Await the successful completion of the ``service-re-index-dicom-data`` DAG as well as any service-extract-metadata DAGs. When finished none of this DAGs should have operators in the running or queued state.
#. Generate the thumbnails (used as preview images in the Datasets view):
    
    #. Open the ``code-server`` from the Extensions view.
    
    #. In file ``mounted/workflows/dags/dag_service_segmentation_thumbnail.py`` set ui_visible from False to True. This change may take 2-3 minutes to be visible in the frontend. 
        
        .. image:: https://codebase.helmholtz.cloud/-/project/2521/uploads/58bc36bb3215c0efe5856e5155cb242a/image.png
            :width: 295 
            :height: 210
    
    #. In the Workflows > Dataset view click on RTSTRUCT and SEG in the Dashboard on the right side to add both to the filters, then click the SEARCH button so that all RTSTRUCT and SEG objects are selected.
    
    #. Click the Play button and select the ``service-segmentation-thumbnail workflow`` and trigger it.
    
    #. After the ``service-segmentation-thumbnail`` is completed and the thumbnails have been generated reset the ``ui_visible`` of the ``service-segmentation-thumbnail`` from ``False`` to ``True`` again.

#. When everything works in the new version the old data can be deleted using: ``sudo rm -rf /home/kaapana_0.1.3``