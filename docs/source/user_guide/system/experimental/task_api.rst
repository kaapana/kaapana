.. _experimental_task_api:

Task API
^^^^^^^^
.. warning::
   Experimental and not yet the default. 

  
The Task API defines a **contract for processing-containers** so that running one only requires pointing it at input and output data.
It has two parts:

- a :code:`processing-container.json` that describes how to use a container image
- a **python library** that reads that file, validates a ``Task`` object, runs the container and streams back logs

More details
************

- Service architecture: ``lib/task_api/Readme.md``
- Full reference (``processing-container.json`` schema, installing the library, validating, and running a task locally with Docker), plus how it is wired into the workflow engine via ``KaapanaTaskOperator``: :ref:`Developing a Processing-Container <processing_container_dev_guide>`.

