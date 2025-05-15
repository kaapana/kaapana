.. _workflow_fails_without_logs:

Workflow fails without logs
***************************

.. code-block:: text

    Could not read served logs: Invalid URL 'http://:8793/log/XXX/attempt=3.log': No host supplied

If there are no logs in the Airflow UI and the workflow fails, try to retrace your steps. If you changed some module inside the Airflow scheduler, 
it might be that Airflow can no longer parse the DAG file due to the changes. This is usually caused by a Python error such as an ImportError, 
including issues with imported packages.

In such cases, Airflow cannot register the workflow, and therefore cannot show you logs.

To see the actual error, you can check the Airflow scheduler logs by running:

.. code-block:: bash

    kubectl logs -n services airflow-scheduler-<pod-id>

You can find the `<pod-id>` by using:

.. code-block:: bash

    kubectl get pods -n services
