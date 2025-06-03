.. _workflow_list:

Workflow List
^^^^^^^^^^^^^

The Workflow List component allows users to visualize all workflows that are currently running 
or have previously run on the platform. The Workflow List comes with the following features:

* comprehensive information regarding the specification of each workflow: workflow name, workflow UUID, dataset, time of workflow creation and time of last workflow update, username, owner instance
* live status updates on the jobs associated with each workflow
* set of workflow actions that users can perform, including the ability to abort, restart, or delete workflows and all their associated jobs

Each row of the Workflow List, which represents one workflow, can be expanded to further 
present all jobs which are associated with the expanded workflow. 
This list of job list comes with the following features:

* comprehensive information regarding the specification of each job: ID of Airflow-DAG, time of job creation and time of last job update, runner instance, owner instance (= owner instance of workflow), configuration object, live updated status of the job
* redirect links to the job's Airflow DAG run to access additional details and insights about the job's execution
* redirect links to the Airflow logs of the job's failed operator for troubleshooting and understanding the cause of the failure
* set of job actions that users can perform, including the ability to abort, restart, or delete jobs

.. image:: https://www.kaapana.ai/kaapana-downloads/kaapana-docs/stable/img/wms_workflow_list.png


Service-workflows
""""""""""""""""""

In addition to regular workflows, the Workflow Management System (WMS) also visualizes background 
services within the platform. These services, such as pipelines triggered whenever a DICOM image 
arrives, are represented as service workflows accompanied by service jobs. 
By incorporating these service workflows into the visualization, users can easily track 
and monitor the execution of these important background processes within the platform.

.. note::
    Service workflows are only visible in the _admin_ project, as they are not associated with any specific project.