.. _experimental_data_api:

Data API
^^^^^^^^

.. warning::

   Experimental and not yet the default. 

The **Data API** is the first version of Kaapana's new explicit data layer. It introduces a generic model for describing data in the platform as addressable **data entities** with structured metadata, related artifacts and storage coordinates.

Historically, Kaapana has been centered around DICOM series. Additional information such as tags, datasets, validation results, thumbnails and reports was stored across different services and databases. This worked well for classical imaging workflows, but made it difficult to handle other data types in a consistent way.

The Data API changes this by separating the question **what data exists and how it is described** from the question **where the raw files are stored**. A data entity can represent a DICOM series, but the same concept can also be used for other file-based or derived data, such as masks, reports, statistical results, workflow outputs or, in future versions, trained models and datasets.

A data entity contains:

- a stable entity identity
- typed metadata attached through registered metadata schemas
- references to artifacts such as thumbnails, reports or result files
- storage coordinates pointing to the underlying data
- relations to other entities, where applicable

This makes the model flexible without requiring every data type to be built into the core platform. New data types can be introduced by defining suitable metadata schemas, storing the corresponding files in a supported storage backend and registering the resulting entity in the Data API.

Using it
********

The current experimental implementation can be inspected in the web UI under:

``Experimental`` / ``Data``

There, users can:

- create and run queries against the Data API
- inspect matching data entities
- view and edit metadata attached to entities
- inspect registered artifacts and storage coordinates

As an initial use case, incoming DICOM series are registered as Data API entities during ingestion. This demonstrates the core idea: every series becomes an addressable entity, DICOM metadata is attached through schemas, and related artifacts such as thumbnails or validation reports can be linked to the same entity.

What is included in v1
**********************

The current v1 focuses on the foundation of the new model:

- generic data entities as the central representation of platform data
- metadata schemas for structured, typed metadata
- metadata attachment to existing entities
- artifact registration and upload
- storage coordinates for locating the underlying files
- query access through the Data API
- experimental UI support for browsing entities and metadata
- initial DICOM-series ingestion into the Data API model

At this stage, the Data API should be understood as an experimental metadata and query layer. It does **not** replace a PACS, object storage or the workflow engine. Raw data remains in the corresponding storage backend, while the Data API stores the entity identity, metadata and references required to work with it.

Roadmap
*******

The next step is to lift the Data API from the current v1 foundation to a broader v2 data layer.

Planned v2 work includes:

- first-class support for **datasets** as Data API concepts
- support for **models** and other non-DICOM artifacts as managed data entities
- a dedicated **Storage API** to abstract access to the underlying storage backends
- stronger integration of the Data API into workflows and platform services
- a clearer path toward replacing direct dependencies on older DICOM- and OpenSearch-centered data paths

With these additions, the Data API is expected to become the common access layer for different kinds of platform data, not only imaging data. This should make it easier to build workflows that consume heterogeneous inputs, produce reusable outputs and manage computational experiment results inside Kaapana.

More details
************

- Concept, data model, query model and implementation notes: ``services/base/data-api/README.md``.