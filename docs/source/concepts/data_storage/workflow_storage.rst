.. _concepts_workflow_storage:

Workflow Storage
################################

A workflow's first task typically fetches its input itself: the ``GetInputOperator`` container talks DICOMweb directly to the PACS over the network and writes the result into the run's project-scoped ``workflow-data-pv-claim`` PVC, which the Airflow adapter (see :ref:`concepts_architecture`) mounts via the project's ``project-runtime`` service.
From there on, handing data between tasks does not repeat that network fetch: the :ref:`Task API<concepts_architecture>` lets a task template declare named input and output channels, and ``KaapanaTaskOperator``'s ``iochannel_maps`` wires an upstream task's output channel to a downstream task's input channel through the same mounted PVC.
