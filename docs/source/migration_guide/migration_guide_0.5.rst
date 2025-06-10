.. _migration_guide_0.5:

Migration from Version 0.4.2 to 0.5.0
*************************************

Version 0.5.0 introduces migration versioning, which requires a few additional steps to upgrade existing platforms from the previous release. This mechanism lays the foundation for easier migrations in the future.

Migration Process Overview
==========================

To update existing platforms from version 0.4.2 to 0.5.0, follow the steps below:

1. Backup your FAST_DATA_DIR (``/home/kaapana``)
2. Run the migration script:

   .. code-block:: bash

      sudo ./kaapana/utils/migration-0.4.2-0.5.0.sh

Important Changes and Manual Steps
==================================

- **Thumbnails Migration:** Not supported. Thumbnails must be regenerated manually described in the note below.

.. note::

   For thumbnail generation to work correctly after the migration, you must:

   - Clear the existing validation results
   - Re-run the **validation** workflow
   - Then run the **generate thumbnail** workflow

   This is required because thumbnail generation now depends on metadata produced during the validation completeness check.

- **Project Separation:** The datasets and workflows are no longer visible to all projects and user. They are now project-bound. 
   - **Dataset Assignment:** All existing datasets will be automatically assigned to the `admin` project.
   - **Workflow Assignment:** All previously executed workflows will also be assigned to the `admin` project.

Automatically Migrated Components
=================================

The following components will be migrated automatically during the upgrade:

- Users and their role mappings
- Projects
- Data
- Workflows
- Mappings between the above systems except exceptions mentioned above

Migration Paths for Key Components
==================================

- **DICOM and MinIO Files:** All data from MinIO will remain intact. File paths and structures are preserved.
- **Tags in OpenSearch:** Tags and metadata will be retained and remain accessible post-migration.
- **User Accounts and Role Mappings:** Users, roles, and associated permissions are automatically migrated.
- **Kaapana Federated Sites:** Registered sites will be preserved; no additional steps are required.
- **Workflows:** Existing workflows will be migrated.