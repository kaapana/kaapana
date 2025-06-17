.. _wms_start:


Workflows
##########

Starting from Kaapana version 0.2.0, the Kaapana platform is equipped with a 
Workflow Management System (*WMS*) including views for :ref:`uploading data<data_upload>`,   
for :ref:`data inspection<datasets>`, :ref:`workflow overview<workflow_list>`, and more.
The WMS allows the user to interact with the Kaapana object :term:`workflow`. 
The workflow object semantically binds together multiple :term:`jobs<job>`, their processing data, 
and the orchestrating- and runner-instances of those jobs. 
In order to manage these workflows, the WMS comes with three components:
:ref:`workflow_execution`, :ref:`workflow_list` and :ref:`instance_overview`.

.. important::
    All resources and objects that are managed by the WMS are separated by :term:`projects<project>`.
    I.e. the WMS will only show workflows, dicom-series, datasets and workflows that are associated with the currently selected project.

.. toctree::
    :maxdepth: 2

    workflow_management_system/data_upload
    workflow_management_system/datasets
    workflow_management_system/workflow_execution
    workflow_management_system/workflow_list
    workflow_management_system/instance_overview
    workflow_management_system/active_applications
