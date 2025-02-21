.. _migration_guide:

########################
Migration Guide
########################


+-------+-------+---------------------------+--------------------------+
| From  | To    |   What is preserverd?     |    What is lost?         |
+=======+=======+===========================+==========================+
| 0.3.X | 0.4.X |  - Datasets               |                          |
|       |       |  - Airflow logs           |                          |
|       |       |  - Images in Pacs         |                          |
|       |       |  - Metadata in Opensearch |                          |
|       |       |  - Keycloak user          |                          |
|       |       |  - Generated thumbnails   |                          |
|       |       |  - Static website results |                          |
+-------+-------+---------------------------+--------------------------+
| 0.2.X | 0.3.X |  - Images in PACS         |                          |
|       |       |  - Metadata               |                          |
+-------+-------+---------------------------+--------------------------+
| 0.1.3 | 0.2.X |  - Images in PACS         |  - Airflow Logs          |
|       |       |  - Datasets               |  - Airflow Configuration |
|       |       |  - Workflows              |                          |
+-------+-------+---------------------------+--------------------------+


.. toctree::
    :maxdepth: 3

    migration_guide/migration_guide_0.4
    migration_guide/migration_guide_0.3
    migration_guide/migration_guide_0.2
