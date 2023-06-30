.. _operator_not_started:

Operator hangs in *scheduled* state
*************************************

.. image:: https://www.kaapana.ai/kaapana-downloads/kaapana-docs/stable/img/operator_not_started.png


If a task of a DAG-run is not started and hangs in the *scheduled* state, it could be due to insufficient resources on the host machine to start the operator. 
The image above illustrates how this situation would appear in Airflow.
If you wish to run the operator anyway, you can manually decrease the value of :code:`ram_mem_mb` in the operator's code using the code-server extension.

.. warning:: 
    The :code:`ram_mem_mb` variable defines the amount of memory allocated to this operator. 
    If it is set too low, the operator might fail since the operation requires more memory than what has been allocated.

.. image:: https://www.kaapana.ai/kaapana-downloads/kaapana-docs/stable/img/adjust_ram_mem_mb.png



After decreasing the value for :code:`ram_mem_mb`, you need restart the task by following these steps:

    1. Navigate to Airflow and access the graph view of the workflow containing the unstarted task.
    2. Click on the specific task, and in the resulting pop-up window, click on Clear.
    3. This action will restart the selected task as well as all downstream tasks associated with it."

Alternatively, you can :ref:`restart the entire job<how_to_stop_and_restart_workflows>` through the Workflow Execution page.



