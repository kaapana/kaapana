.. _migration_guide_0.3:

Migration from Version v0.2.x to v0.3.x
***************************************

This guide walks you through the process of migrating from Kaapana v0.2.x to v0.3.x. 
The metadata stored in OpenSearch does not require migration as it is compatible with the new version. 
However, DICOM data managed by dcm4che requires specific steps to ensure a successful migration.

DICOM Data Migration in dcm4che
-------------------------------

This section provides a step-by-step guide for migrating DICOM data in dcm4che. 
The instructions are based on the official upgrade guides for dcm4che:

**References**:
    - `Upgrade-on-Docker <https://github.com/dcm4che/dcm4chee-arc-light/wiki/Upgrade-on-Docker>`_
    - `General Update Guide <https://github.com/dcm4che/dcm4chee-arc-light/wiki/Upgrade>`_

#. Start the existing dcm4che-Postgres Database
    Begin by starting the dcm4che-Postgres container for version 0.2.x. 
    This container should access the same database as the current running instance of Kaapana but ensure no interactions with dcm4che occur (e.g., avoid sending new data).

    .. code-block:: shell

        docker run --name db \
                    -it --rm \
                    -p 5432:5432 \
                    -e POSTGRES_DB=pacsdb \
                    -e POSTGRES_USER=pacs \
                    -e POSTGRES_PASSWORD=pacs \
                    -v ${SLOW_DATA_DIR}/postgres-dcm4che:/var/lib/postgresql/data \
                    -d <image-dcm4che-postgres:0.2.x>
    
#. Verify the Current Database
    Check the current state of the database and note down key counts:

    .. code-block:: shell
        
        docker exec -it db bash

        psql $POSTGRES_DB $POSTGRES_USER
        
        \dt
        SELECT storage_path FROM public.location;
        SELECT series_iuid FROM public.series;
        SELECT COUNT(series_iuid) FROM public.series;
        SELECT COUNT(sop_iuid) FROM public.instance;

#. Create a Backup (SQL Dump)
    Create an SQL dump of the current database. First, ensure you have a backup directory, e.g., ``/home/kaapana/backup``.

    .. code-block:: shell

        docker exec -t db pg_dump -U pacs -d pacsdb > /home/kaapana/backup/pacsdb_9_6.sql

    .. note::

        Alternative dump formats (e.g., ``pg_dump -Fc``) may lead to import errors. 
        To avoid corrupted databases, we recommend using a plain SQL dump.

#. Prepare the Update Scripts
    Download the required update scripts from the dcm4che repository.
    Clone the dcm4che repository or access the SQL scripts directly:

    .. code-block::

        curl https://github.com/dcm4che/dcm4chee-arc-light/tree/master/dcm4chee-arc-entity/src/main/resources/sql/psql

#. Stop and Remove the Existing Container
    Stop and remove the current database container:

    .. code-block:: shell

        docker stop db
        docker rm db

#. Start a New Container with Update Scripts
    Start a new container with the update scripts mounted as a volume:

    .. code-block:: shell

        docker run --name db \
                    -it --rm \
                    -p 5432:5432 \
                    -e POSTGRES_DB=pacsdb \
                    -e POSTGRES_USER=pacs \
                    -e POSTGRES_PASSWORD=pacs \
                    -v ${FAST_DATA_DIR}/postgres-dcm4che9.6:/var/lib/postgresql/data \
                    -v /path/to/repository/dcm4chee-arc-light/dcm4chee-arc-entity/src/main/resources/sql/psql:/update \
                    -d <image-dcm4che-postgres:0.2.x>


#. Import the SQL Dump
    Restore the database from the SQL dump:

    .. code-block:: shell

        docker cp /home/kaapana/backup/pacsdb_9_6.sql db:/pacsdb_9_6.sql
        docker exec -it db bash
        
        psql -U pacs -d pacsdb
        
        SET session_replication_role = 'replica';
        \i /pacsdb_9_6.sql
        SET session_replication_role = 'origin';

    .. note::

        Temporarily disabling foreign key constraints during import helps avoid violations and ensures smooth data restoration.

#. Verify Data Integrity
    Compare the restored database against the original counts.
    Execute the following commands while still in the db container and the psql terminal:

    .. code-block:: shell
        
        \dt
        SELECT storage_path FROM public.location;
        SELECT series_iuid FROM public.series;
        SELECT COUNT(series_iuid) FROM public.series;
        SELECT COUNT(sop_iuid) FROM public.instance;

#. Apply Database Updates
    Update the database schema incrementally using the SQL scripts.
    Execute the following commands while still in the db container and the psql terminal:

    .. code-block:: shell

        psql $POSTGRES_DB $POSTGRES_USER -a -f /update/update-5.27-psql.sql
        psql $POSTGRES_DB $POSTGRES_USER -a -f /update/update-5.28-psql.sql
        psql $POSTGRES_DB $POSTGRES_USER -a -f /update/update-5.29-psql.sql
        psql $POSTGRES_DB $POSTGRES_USER -a -f /update/update-5.30-psql.sql
        psql $POSTGRES_DB $POSTGRES_USER -a -f /update/update-5.31-psql.sqls
        psql $POSTGRES_DB $POSTGRES_USER -a -f /update/update-5.31.1-psql.sql
        psql $POSTGRES_DB $POSTGRES_USER -a -f /update/update-5.32-psql.sql

#. Create a New Backup
    - Exit the current container.
    - Create a new SQL dump of the updated database:

    .. code-block:: shell

        docker exec -t db pg_dump -U pacs -d pacsdb > /home/kaapana/backup/pacsdb_updated.sql

#. Deploy the Updated Database
    Deploy the updated database using the Kaapana v0.3.x dcm4che-Postgres image:

    .. code-block:: shell

        docker run --name db15 \
                    -it --rm \
                    -p 5432:5432 \
                    -e POSTGRES_DB=pacsdb \
                    -e POSTGRES_USER=pacs \
                    -e POSTGRES_PASSWORD=pacs \
                    -v /home/kaapana/postgres-dcm4che-new:/var/lib/postgresql/data \
                    -d <kaapana-image-dcm4che-postgres:0.3.x>


#. Replace old database
    - Replace the old database directory with the updated one.
    - Delete intermediate directories.
        
        .. code-block:: shell
            
            sudo mv /home/kaapana/postgres-dcm4che /home/kaapana/postgres-dcm4che-old
            sudo mv /home/kaapana/postgres-dcm4che-new /home/kaapana/postgres-dcm4che
            sudo rm -rf /home/kaapana/postgres-dcm4che9.6

#. Redeploy Kaapana v0.3.x
    - Follow the :ref:`Deployment Guide<deployment>`.
    - Ensure that ``SLOW_DATA_DIR`` points to the correct path.

#. Update the LDAP schema and data as required.
    - Login to the platform and open the Kubernetes dashboard.
    - Find the ldap pod and access it.
    - Then run the following commands:

        .. code-block:: shell

            update-schema
            export ARCHIVE_DEVICE_NAME=KAAPANA
            update-data 5.28.0
            update-data  5.29.0                      
            update-data  5.29.1                  
            update-data  5.29.2                             
            update-data  5.30.0   
            update-data 5.31.0          
            update-data 5.31.1
            update-data 5.32.0

            init-role auth root
            assign-role-to-user auth user
            assign-role-to-user auth admin
            unassign-role-from-user auth root
            unassign-role-from-user auth admin
            
        .. note::        

            It is ``unassign-role-from-user`` and not ``unassign-role-to-user``!

#. Restart dcm4che and ldap pods 
    You can either delete the pods using the Kubernetes dashboard or in the terminal with ``kubectl delete pod``.