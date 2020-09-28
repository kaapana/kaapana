.. _update_1.1_doc:

Version 1.1
===========

| This update includes several major changes see the :ref:`Update changelog` for more information.
| We also included some new pipelines in the deployment, which are described in :ref:`workflow start`. 


.. _Update backup:

How to backup your DICOM data
-----------------------------

If you already have collected valuable DICOM data, you can create a backup snapshot of the data storage.

Create the snapshot:  
::

    lvcreate -s  -l50%FREE -n dicom-backup  /dev/mapper/vg--hdd-mnt_dicom

After a successful update of the platform, you can remove the snapshot with: 
::

    lvremove /dev/vg-hdd/dicom-backup


.. _Update migrate:

How to update from JIP v1.0.1
-----------------------------
.. hint::

    If there is not yet any critical data on the server, the simplest way to update the system is to delete all persisted files and re-deploy the platform as described in: :ref:`Update reset`.
    

.. warning::

  | **The following components will be reset during the update!**
  | - Airflow, DAGs, operators and corresponding databases
  | - Files in Minio
  | - Elasticsearch
  | - Kibana
  | - Dcm4chee
  | *Make sure to backup your custom files like DAGs, operators etc.*
  | **All existing DICOM images, segmentations etc. will be kept in this process!**  


You can update the system directly on the server or remote from your machine via ssh.

**1. Check JIP deloyment:**
::

    helm ls
    > jip 	1       	Tue Nov 19 13:38:17 2019	DEPLOYED	joint-imaging-platform-1.0.1	1.0.1      	default  

In case you get an "command not found"

Please enter:
::
    
    export PATH=/usr/local/bin:$PATH
    export PATH=/usr/local/bin:$PATH > /etc/profile.d/helm_init.sh
    chmod +x /etc/profile.d/helm_init.sh

Now "helm ls" should work!

**2. Remove old jip delpoyment:**
::

    helm del jip --purge
    > release "jip" deleted

    

**3. Check where the dicom data is stored (typically /mnt/dicom).**

This can be checked by:

::

    ls /mnt/dicom
    > dcm4che

There should be a /mnt/dicom/**dcm4che** directory. 

.. warning::

  | **If there is no "dcm4che" directory**
  | *However, if you initially installed Release 1.0, there was a bug in the default configuration.*
  | *Dicom data should be located at /home/kaapana/dcm4che/dicom_data*
  | Try:
  |
  |     ls /home/kaapana/dcm4che/
  |     > server_data    dicom_data
  | 
  | To move the data use:
  |     *mv /home/kaapana/dcm4che/dicom_data /mnt/dicom/TMP/* 
  | and skip step 5.

**4. Create temporary directory for dicom data**

execute:

::

    mkdir -p /mnt/dicom/TMP

**5. Save DICOM data**

Move data from **/mnt/dicom/dcm4che** to **/mnt/dicom/TMP/**
::

    mv /mnt/dicom/dcm4che/dicom_data /mnt/dicom/TMP/
    rm -rf /mnt/dicom/dcm4che

While installing the release 1.1 the files in the directory "/mnt/dicom/TMP" will be automtically moved and deleted.

**6. Check where the persited data is stored (Usually /home/kaapana).**

This can be checked by:

::

    ls /home/kaapana
    > airflow  ctp  dcm4che  elastic-meta  ldap  minio  postgres-airflow  postgres-dcm4che  postgres-keycloak  prometheus  slapd.d  traefik  workflows

You should see a similar list of directories.

**7. Delete persited data**


Delete Elasticsearch data
::

    rm -rf /home/kaapana/elastic-meta

Delete Minio data
::

    rm -rf /home/kaapana/minio

Delete Dcm4che data
::

    rm -rf /home/kaapana/dcm4che

Delete Dcm4che database data
::

    rm -rf /home/kaapana/postgres-dcm4che

Delete Airflow data
::

    rm -rf /home/kaapana/airflow/

Delete Airflow database data
::

    rm -rf /home/kaapana/postgres-airflow/

Delete workflow data
::

    rm -rf /home/kaapana/workflows/

**8. Platform deployment**

You can now continue with :ref:`installation deployment`.

.. hint::

    Default values will not be restored! -> credentials will still be valid
    
    The re-indexing of the images will take some time.
    They should show up after a while, though.
    


.. _Update reset:

Fresh installation
------------------

.. warning::

  | **All persisted data will be deleted.**
  | *This includes both dicom/processing data and custom configurations like:*
  | - Keycloak LDAP authentication
  | - Custom Airflow processing DAGs and operators
  | - Files stored in Minio
  | - ...

**1. Delete persisted data**
::

    rm -rf /home/jip

**2. Delete dicom data**
::

    rm -rf /mnt/dicom/*

You can now continue with :ref:`installation deployment`.



.. _Update changelog:

Changelog
---------

BASE
^^^^
- Landing-page updated to v1.1
- OHIF Viewer updated

STORE
^^^^^
- Dcm4chee updated to v5.19.0
- Min.io updated to RELEASE.2019-10-12T01-39-57Z


FLOW
^^^^
- New workflow distribution method via Helm and Docker containers

- Airflow updated to v1.10.6
    - Support for manual operators with user-interaction / web-services
    - New kaapana plugin with all airflow adaptations
    - Integration of a platform API for job interaction
    - New directory structure for temporary data

- CTP updated to v2019.06.18
    - updated CTP dag-trigger pluging (-> improved with circular buffers)

- Image-fetcher updated


META
^^^^
- Kibana updated to v6.8.12
    - Update of the "start-process" plugin 
    - New init-job for META including field formatting 
    - New dashboard design 

- Elasticsearch updated to v6.8.12
- Improved extract-metadata workflow

SYSTEM
^^^^^^
- Traefik updated to v1.7.19
- Keycloak updated to v7.0.1
- Gatekeeper updated to v7.0.0
- Server timeout bugfix


MONITORING
^^^^^^^^^^
- Kubernetes Dashboard updated to v2.0.0-beta5
- Added GPU Prometheus exporter for gpu monitoring
- Grafana updated to v6.4.4
    - New GPU monitoring dashboard
    - New Kubernetes dashboard design
    - User login is now managed by Single Sign-on

- Prometheus updated to v9.6-alpine
- Alertmanager updated to v0.21.0
