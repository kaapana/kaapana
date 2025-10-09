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

Not Included
============
- Automatic thumbnail generation for old files
- Automatic validation rerun for legacy datasets

- **Manual Thumbnail Generation:**  

  In earlier versions, thumbnails (stored in MinIO) were not generated. Therefore, existing data from those versions does not contain thumbnails.
  Thumbnails can be generated retroactively, but the thumbnail DAG relies on validation completeness, which may be missing in older validation entries.
  To ensure consistent and reliable thumbnail generation, we recommend running the following DAGs in sequence:

  1. `clear-validation-results`
  2. `validate-dicoms`
  3. `generate-thumbnail`

  This process will create consistent thumbnails according to the newer validation and generation logic.

Migrate
=======
To update existing platforms' databases from version 0.4.x to 0.5.x, follow the steps below:

1. Undeploy Kaapana platform
  
   .. code-block:: bash

      ./deploy_plaform.sh --undeploy

2. Wait until fully undeployed

  - `helm ls -a` does not show any Kaapana deployment
  - `kubectl get pods -A` does not show any Kaapana pods, only `kube-system` namespace
    
3. Backup your `FAST_DATA_DIR`
   
   .. code-block:: bash

      cp -a <FAST_DATA_DIR>/* /path/to/backup

4. Get the migration script - either clone the kaapana repository or download the script directly:

   .. code-block:: bash

      git clone https://codebase.helmholtz.cloud/kaapana/kaapana/

5. Run the migration script with specified FAST_DATA_DIR:

   .. code-block:: bash

      sudo ./kaapana/utils/migration-0.4.x-0.5.x-0.sh <FAST_DATA_DIR>

6. Deploy kaapana and wait until all pods are Completed or Running state:

   .. code-block:: bash

      ./deploy_platform.sh


Operators and Workflows Changes
===============================

- `KaapanaBaseOperator` now accepts a new parameter: `display_name`

- Operator configuration:
  
  - `conf["form_data"]` has been removed
  - Use `conf["workflow_form"]` instead

- MinIO access updated:
  
  - Use `kaapanapy.get_minio_client()` function
  - Deprecated: `kaapanapy.helper.get_minio_client.HelperMinio` class

- `DcmSendOperator`:
  
  - New default parameters:
  
    - `ram_mem_mb=50`
    - `ram_mem_mb_lmt=4000`

- `GetThumbnailOperator`:
  
  - Environment variable changed from `ORIG_IMAGE_OPERATOR_DIR` to `GET_REF_SERIES_OPERATOR_DIR`

- New Operators:
  
  - `NotifyOperator`
  - `LocalRemoveDicomTagsOperator`
  - `LocalDcmBranchingOperator`

- Label updates:
  
  - `TrainingOperator` and `SegmentationEvaluationOperator` now use:
    
    .. code-block:: json

       {"network-access-opensearch": "true"}

    instead of:

    .. code-block:: json

       {"network-access": "opensearch"}

- DAG Renames:
  
  - `convert-nifitis-to-dicoms-and-import-to-pacs` → `import-niftis-from-data-upload`
  - `import-dicoms-in-zip-to-internal-pacs` → `import-dicoms-from-data-upload`