.. _experimental_data_api:

Data API
^^^^^^^^

.. warning::

   Experimental and not yet the default. 

``data_api`` is the async client library (SDK) that gives Python callers (operators, processing containers, backend services) programmatic access to the Kaapana **Data API** and **Storage API**. 
It ships two async clients:

- **``DataClient``**: query/index entities, create entities, register metadata schemas, attach metadata, upload artifacts
- **``StorageClient``**: bulk download of entity files as an unpacked tar archive

More detail
***********

- Full API reference and examples: ``lib/data_api/README.md``.
