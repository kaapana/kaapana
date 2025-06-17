.. _migration_guide_0.5:

Migration from Version 0.4.2 to 0.5.0
*************************************

Version 0.5.0 introduces migration versioning, which requires a few additional steps to upgrade existing platforms from the previous release. This mechanism lays the foundation for easier migrations in the future.

Migration Process Overview
==========================

1. Migrate databases (workflows, projects, users, roles, mappings, registered kaapana-sites)
2. Migrate DICOM data
3. Migrate OpenSearch
4. Migrate Minio

1. Migrate databases 
====================
To update existing platforms' databases from version 0.4.x to 0.5.x, follow the steps below:

1. Backup your FAST_DATA_DIR (``/home/kaapana``)
2. Run the migration script:

   .. code-block:: bash

      sudo ./kaapana/utils/migration-0.4.2-0.5.0.sh