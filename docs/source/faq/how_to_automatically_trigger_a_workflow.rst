How to automatically trigger a workflow
=======================================

LocalAutoTriggerOperator
---------------------------------
To automatically trigger workflows configuration JSON files with the name */*trigger_rule.json* are needed. The operator *LocalAutoTriggerOperator* search for all files with this extension in the dags folder.
And add the operator LocalAutoTriggerOperator to your workflow.

Example:

.. code-block::

      [
         {
            "search_tags": {},
            "dag_ids": {
                  <dag id to trigger>: {
                     "fetch_method": "copy",
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