.. _migration_guide_0.5:

Migration from Version 0.4.1 to 0.5.0
*************************************

Version 0.5.0 introduces migration versioning which introduces few additional steps to perform migration, that will ease any future migrations.

To migrate database data for dicom-web-filter, access-information-interface and kaapana-backend, follow these steps:

1. Each component needs to be stamped with the alembic version, for migration to know where is it currently. 
2. Execute into the pod and run alembic stamp <revision>
    - dicom-web-filter `alembic stamp b2c8d2f8b682`
    - kaapana-backend `alembic stamp --purge 5d694eb1a7b1``
    - access-information-interface `alembic stamp 100ab450e292``