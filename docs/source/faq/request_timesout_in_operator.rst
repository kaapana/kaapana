.. _request_timeouts_in_operator:

Operator fails, because a request times out
*******************************************

If your custom operator makes a request to another service or an external IP it may fail with an error similar to the one below.

:code:`ConnectTimeoutError((<urllib3.connection.HTTPConnection object at 0x7f8c4ba78e20>, 'Connection to opensearch-service.services.svc timed out. (connect timeout=2)'))`

This can happen, when a :ref:`Network Policy <network_policies>` restricts the pod from making requests to the desired service.
You might need to add the `network-access` label with the correct value to the operator.
A list of possible values can be found :ref:`here <network_policies>`.
You can set this label either in the operator definition or when you use the operator in a DAG:

.. code-block:: python
    
    task_with_access_to_opensearch = MyCustomOperator(
        dag=dag,
        labels={"network-access": "opensearch"},
    )
