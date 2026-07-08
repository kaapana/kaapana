.. _concepts_workflow_storage:

Workflow Storage
################################

By default, data is fetched from the local PACS into the project-scoped ``workflow-data-pv-claim`` PVC, which the Airflow adapter (see :ref:`concepts_architecture`) mounts into a workflow's processing pods via the project's ``project-runtime`` service. A pod reads its input from that mounted volume; it does not fetch it from the PACS over the network itself.
A pod's results are handed to the next pod the same way: the :ref:`Task API<concepts_architecture>` lets a task template declare named input and output channels, and ``KaapanaTaskOperator``'s ``iochannel_maps`` wires an upstream task's output channel to a downstream task's input channel -- the same PVC-mounting mechanism.
