.. _migration_guide_0.3:

Migration from Version v0.2.x to v0.3.x
***************************************

The current default way to go, is delete `SLOW_DATA_DIR` and `FAST_DATA_DIR` (e.g. /home/kaapana) and start fresh. 
If data has to be kept (images in PACs and META) one has to copy the dcm4che data (from SLOW_DATA_DIR) and reimport and or reindex with the corresponding dags.
This is the safest way and is still a valid option (since we have still 0.x version). 


So this focuses only on the most important databases (PACs and META). 
Meta has not to be migrated (works out of the box).   

For dcm4che:   

**Sources**
* `Upgrade-on-Docker <https://github.com/dcm4che/dcm4chee-arc-light/wiki/Upgrade-on-Docker>`_
* `Update general <https://github.com/dcm4che/dcm4chee-arc-light/wiki/Upgrade>`_

1. We start by starting dcm4che-postgres with the 0.2.x version the kaapana instance is running on (the intance can still be running, but do not interact with dcm4che (e.g. send new data):

    .. code-block:: shell

        docker run --name db \
                    -it --rm \
                    -p 5432:5432 \
                    -e POSTGRES_DB=pacsdb \
                    -e POSTGRES_USER=pacs \
                    -e POSTGRES_PASSWORD=pacs \
                    -v /home/kaapana/postgres-dcm4che:/var/lib/postgresql/data \
                    -d <image-dcm4che-postgres:0.2.x>
        
        docker exec -it db bash

2. Start check to current database and note down the COUNTS:

    .. code-block:: shell

        psql $POSTGRES_DB $POSTGRES_USER
        pacsdb=# \dt
        pacsdb=# SELECT storage_path FROM public.location;
        pacsdb=# SELECT series_iuid FROM public.series;
        pacsdb=# SELECT COUNT(series_iuid) FROM public.series;
        pacsdb=# SELECT COUNT(sop_iuid) FROM public.instance;

Create an SQL DUMP, create a backup location first (e.g. ``/home/kaapana/backup``)

    .. code-block:: shell

        docker exec -t db pg_dump -U pacs -d pacsdb > /home/kaapana/backup/pacsdb_9_6.sql

    .. note::
        I also tried creating dumps, e.g. ``docker exec -t db  pg_dump -U pacs -d pacsdb -Fc -f  /pacsdb_9_6.dump``  and restored with ``pg_restore -U pacs -d pacsdb -v /pacsdb_9_6.dump``.
        But I cannot recommend it, since I got import errors, resulting in corrupted databases.



Next, we need the update folder on dcm4che (clone dcm4che from github or this folder: https://github.com/dcm4che/dcm4chee-arc-light/tree/master/dcm4chee-arc-entity/src/main/resources/sql/psql   

Stop and delete the current container first

    .. code-block::

        docker stop db
        docker rm db

Start a new docker **with different volume-mounts**!  

    .. code-block:: shell 

        docker run --name db \
                    -it --rm \
                -p 5432:5432 \
                -e POSTGRES_DB=pacsdb \
                -e POSTGRES_USER=pacs \
                -e POSTGRES_PASSWORD=pacs \
                -v /home/kaapana/postgres-dcm4che9.6:/var/lib/postgresql/data \
                -v /home/ubuntu/update-dcm4che/dcm4chee-arc-light/dcm4chee-arc-entity/src/main/resources/sql/psql:/update \
                -d <image-dcm4che-postgres:0.2.x>

Next, import the sql dump into the new database.

    .. code-block:: shell

        docker cp /home/kaapana/backup/pacsdb_9_6.sql db:/pacsdb_9_6.sql
        docker exec -it db bash
        psql -U pacs -d pacsdb
        SET session_replication_role = 'replica';
        \i /pacsdb_9_6.sql
        SET session_replication_role = 'origin';

Make sure to use the set functions: By temporarily disabling foreign key constraints, you can import your data without encountering foreign key violations. 
Because otherwise, I encountered errors when importing (also with pg_restore).

Check if the database is complete, e.g. compare:

    .. code-block:: shell

        psql $POSTGRES_DB $POSTGRES_USER
        pacsdb=# \dt
        pacsdb=# SELECT storage_path FROM public.location;
        pacsdb=# SELECT series_iuid FROM public.series;
        pacsdb=# SELECT COUNT(series_iuid) FROM public.series;
        pacsdb=# SELECT COUNT(sop_iuid) FROM public.instance;

Next, update the database tables, by updating version by version:

    .. code-block:: shell

        psql $POSTGRES_DB $POSTGRES_USER -a -f /update/update-5.27-psql.sql
        psql $POSTGRES_DB $POSTGRES_USER -a -f /update/update-5.28-psql.sql
        psql $POSTGRES_DB $POSTGRES_USER -a -f /update/update-5.29-psql.sql
        psql $POSTGRES_DB $POSTGRES_USER -a -f /update/update-5.30-psql.sql
        psql $POSTGRES_DB $POSTGRES_USER -a -f /update/update-5.31-psql.sql
        psql $POSTGRES_DB $POSTGRES_USER -a -f /update/update-5.31.1-psql.sql
        psql $POSTGRES_DB $POSTGRES_USER -a -f /update/update-5.32-psql.sql

Next, create a new sql dump (like before)

    .. code-block:: shell

        docker exec -t db pg_dump -U pacs -d pacsdb > /home/kaapana/backup/pacsdb_updated.sql

Next, start a new container with the new kaapana dcm4che-postgres image (e.g. <registry.hzdr.de>/<project>/dcm4che-postgres:0.3.x)

    .. code-block:: shell

        docker run --name db15 \
                    -it --rm \
                    -p 5432:5432 \
                    -e POSTGRES_DB=pacsdb \
                    -e POSTGRES_USER=pacs \
                    -e POSTGRES_PASSWORD=pacs \
                    -v /home/kaapana/postgres-dcm4che-new:/var/lib/postgresql/data \
                    -d <kaapana-image-dcm4che-postgres:0.3.3>

        docker cp /home/kaapana/backup/pacsdb_updated.sql db15:/pacsdb_updated.sql
        docker exec -it db15 bash
        psql -U pacs -d pacsdb
        SET session_replication_role = 'replica';
        \i /pacsdb_updated.sql
        SET session_replication_role = 'origin';

kill container  undeploy old kaapana version and rename database:

    .. code-block:: shell

        sudo mv /home/kaapana/postgres-dcm4che /home/kaapana/postgres-dcm4che-old
        sudo mv /home/kaapana/postgres-dcm4che-new /home/kaapana/postgres-dcm4che

delete intermediate database:

    .. code-block:: shell

        sudo rm -rf /home/kaapana/postgres-dcm4che9.6

Redeploy version with kaapana 0.3.x (the ``SLOW_DATA_DIR`` has to point to the old data dir).

Go in kubernetes, enter the ldap pod (in the service namespace) or use the terminal 

    .. code-block:: shell

        kubectl exec -n services --stdin --tty  <ldap-pod-name> -- /bin/sh

Write the following commands:

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

Restart dcm4che and ldap pod.