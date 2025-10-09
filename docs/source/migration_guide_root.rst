.. _migration_guide:

########################
Migration Guide
########################

+-------+-------+---------------------------+----------------------------------------------+
| From  | To    | What is preserved?        | What is lost?                                |
+=======+=======+===========================+==============================================+
| 0.4.X | 0.5.X | - PACS images             | - CT thumbnails                              |
|       |       | - Opensearch metadata     | - Datasets scoped to admin project only      |
|       |       | - Keycloak users          | - Airflow logs scoped to admin project only  |
|       |       | - Static site results     |                                              |
|       |       | - Workflows               |                                              |
+-------+-------+---------------------------+----------------------------------------------+
| 0.3.X | 0.4.X | - Datasets                |                                              |
|       |       | - Airflow logs            |                                              |
|       |       | - PACS images             |                                              |
|       |       | - Opensearch metadata     |                                              |
|       |       | - Keycloak users          |                                              |
|       |       | - Thumbnails              |                                              |
|       |       | - Static site results     |                                              |
+-------+-------+---------------------------+----------------------------------------------+
| 0.2.X | 0.3.X | - PACS images             |                                              |
|       |       | - Metadata                |                                              |
+-------+-------+---------------------------+----------------------------------------------+
| 0.1.3 | 0.2.X | - PACS images             | - Airflow logs                               |
|       |       | - Datasets                | - Airflow config                             |
|       |       | - Workflows               |                                              |
+-------+-------+---------------------------+----------------------------------------------+

.. toctree::
    :maxdepth: 3

    migration_guide/migration_guide_0.5
    migration_guide/migration_guide_0.4
    migration_guide/migration_guide_0.3
    migration_guide/migration_guide_0.2
