How to automatically trigger a workflow
***************************************

It is possible to create a dag that automatically triggers other dags. 
We use this functionality when processing incoming dicom files.
But there are many more possible usecases.
Take a look at the :ref:`Operator and DAG Documentation<api_documentation_root>` for implementation details.

LocalAutoTriggerOperator
---------------------------------
The LocalAutoTriggerOperator scans the directory :code:`/home/kaapana/workflows/dags` for files with the extension :code:`*trigger_rule.json`, e.g. :code:`dag_service_extract_metadata_trigger_rule.json`.

Example:

.. code-block:: python
   :caption: dag_service_extract_metadata_trigger_rule.json

   [
    {
        "search_tags": {},
        "dag_ids": {
            "service-extract-metadata": {
                "fetch_method": "copy",
                "rest_call": {
                    "global": {}
                },
                "single_execution" : false
            }
        }
    }
   ]  

* Specify specifc DICOM tags as search_tags if desired
* Define the dag id to trigger (<dag id to trigger>)
* Set the fetch_method (e.g. copy data from current dag), else the data will be pulled from the packages
* If it is a batch, to trigger the workflow in single or batch mode.

LocalDagTriggerOperator
---------------------------------
To trigger a single workflow the operator *LocalDagTriggerOperator* with all it's defined paramenters can be used.