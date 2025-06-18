.. _migration_guide_0.5:

Migration from Version 0.4.x to 0.5.x
*************************************

1. Migrate databases (workflows, projects, users, roles, mappings, registered kaapana-sites)
2. Migrate DICOM data
3. Migrate OpenSearch
4. Migrate Minio

Overview
========
All four migration steps are performed automatically by running the provided migration script. In essence, the script renames specific database folders.

There are no naming changes for Minio, DICOM, or OpenSearch. Testing confirms that data in these services remains consistent post-migration, and all information is preserved within the same projects as before.

However, some structural and visibility changes have been introduced in how datasets and workflows are handled in the database:

- **Datasets:**  
  Previously, datasets were globally visible to all users. Post-migration, datasets are project-bound.  
  Existing datasets—due to lack of previous mapping—are now all associated with the **admin** project.

- **Workflows:**  
  Similarly, executed workflows were visible system-wide without project association.  
  After the migration, workflows are now project-scoped. Existing workflows have been assigned to the **admin** project.

- **Thumbnail Generation:**  
  Thumbnails (stored in Minio) were not generated in older versions. As a result, historical data does not include thumbnails.  
  Thumbnails can be retroactively generated, but note that the thumbnail DAG expects validation completeness, which is absent in older validations.  
  To ensure consistency, we recommend running the following DAGs in sequence:

  1. `clear-validation-results`
  2. `validate-dicoms`
  3. `generate-thumbnail`

  This process will create consistent thumbnails according to the newer validation and generation logic.

Migrate
=======
To update existing platforms' databases from version 0.4.x to 0.5.x, follow the steps below:

1. Backup your `FAST_DATA_DIR`
   
   .. code-block:: bash

      cp -a /home/kaapana/* /home/kaapana-backup

2. Run the migration script:

   .. code-block:: bash

      sudo ./kaapana/utils/migration-0.4.x-0.5.x-0.sh

3. Steps 1, 2, 3, and 4 are completed automatically by the script.

Not Included
============
- Automatic thumbnail generation for old files
- Automatic validation rerun for legacy datasets
