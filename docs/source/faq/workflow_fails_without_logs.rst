.. _workflow_fails_without_logs:

Workflow fails without logs
***************************

.. code-block:: text

    Could not read served logs: Invalid URL 'http://:8793/log/XXX/attempt=3.log': No host supplied


If there are not logs in the airflow and the workflow fails, try to retrace your steps. If you changed some module inside the airflow scheduler, 
it might be, that airflow cannot parse the dag file anymore, because of the changes. That is cause by any python error like ImportError including the imported packages.
Then airflow cannot register the workflow and therefore cannot show you logs.

To see the error you can run `kubectl logs -n services airflow-scheduler-<pod-id>`. You can find `<pod-id>` by using `kubectl get pods -A`.

To solve the issue you can either fix the underlying error, revert the changes you made, or restart the airflow-scheduler pod and the errors will be visible in the airflow dashboard.