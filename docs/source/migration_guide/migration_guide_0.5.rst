.. _migration_guide_0.5:

Migration from Version 0.4.2 to 0.5.0
*************************************

Version 0.5.0 introduces migration versioning with few additional steps needed to perform migration.
This will allow easier migrations in the future.

1. Backup up you FAST_DATA_DIR (`/home/kaapana`)
2. Run `sudo ./kaapana/utils/migration-0.4.2-0.5.0.sh`

.. note::

   For thumbnail generation to work correctly after the migration, you must:

   - Clear the existing validation results
   - Re-run the **validation** workflow
   - Then run the **generate thumbnail** workflow

   This is required because thumbnail generation now depends on metadata produced during the validation completeness check.