.. _workflow_not_listed:

Workflow is not listed for workflow execution
**********************************************

Workflow not allowed in the selected project
---------------------------------------------
If you cannot find a workflow in the list of executable workflows in the :ref:`Workflow Execution <workflow_execution>` view, it might be that the workflow is not allowed in the selected project.
A platform administrator can enable the workflow for the project in the :ref:`Project Management <projects>` view.


Worklow list takes time to update
----------------------------------
The list of executable workflows in the :ref:`Workflow Execution <workflow_execution>` view is only refreshed once every minute.
So, if you just installed a workflow-extension or created your own DAG in the vscode application you might have to wait up to 60 seconds until it appears in the list of executable workflows.
This interval is configurable as the parameter ``dag_dir_list_interval`` in the file `airflow.cfg <https://codebase.helmholtz.cloud/kaapana/kaapana/-/blob/master/services/flow/airflow/airflow-chart/files/airflow.cfg?ref_type=heads>`_.
