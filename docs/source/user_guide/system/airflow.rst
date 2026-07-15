.. _airflow:

Airflow
^^^^^^^^^^

In Airflow, we define :term:`Directed Acyclic Graphs (DAGs)<dag>` that build our data-processing pipelines.
These DAGs are composed of multiple :term:`operators<operator>`, each serving a specific task.
Within Kaapana, we categorize operators into two types: :term:`local operators<local-operator>` and :term:`processing-containers<processing-container>`.

Furthermore, Airflow functions as the scheduling system for the :term:`jobs<job>`.
The Airflow user interface offers comprehensive insights into DAGs, DAG runs, and their scheduling details.

The platform comes with several preinstalled DAGs and a large set of :term:`custom operators<operator>`.
Additional DAGs can be installed as :term:`ẁorkflow-extensions<workflow-extension>` in the `Extensions` page.

.. _airflow_execution_model:

Execution model for local operators
***********************************

Kaapana uses Airflow's ``KubernetesExecutor`` for local-operator where tasks should run outside the scheduler, while non-local Kaapana operators continue to start their processing pods through the Kaapana Kubernetes runner.
This distinction is important after moving Airflow data from node-local ``hostPath`` mounts to persistent volume claims (PVCs).

Before this change, :term:`local operators<local-operator>` ran directly inside the Airflow scheduler container.
That worked while the scheduler and task execution could rely on the same node-local ``hostPath`` mounts.
With namespace separation and PVC-based storage, these host paths are no longer mounted across namespaces.
Local operators therefore need their DAG and plugin code to be available in the namespace where the Airflow task is executed.

The executor for local operators is selected from the DAG tags:

.. code-block:: python

    if "service" in dag.tags or "import" in dag.tags:
        executor = "LocalExecutor"
    else:
        executor = "KubernetesExecutor"

DAGs tagged with ``service`` or ``import`` run their local operators with ``LocalExecutor`` in the Airflow scheduler, which is located in the services namespace.
This keeps service workflows close to services-namespace volumes and services-namespace resources.
Local operators in other DAGs run with ``KubernetesExecutor`` and are executed in Airflow worker pods.

Because KubernetesExecutor worker pods can run in project namespaces, they need access to the same DAG and plugin code that the scheduler used to parse the workflow.
Each Airflow worker pod therefore starts an init container named ``sync-dags-plugins``.
This init container copies the scheduler pod's DAG and plugin directories into the worker pod before the task container starts.
This replaces the previous ``hostPath`` based sharing of DAGs and plugins across namespaces.

Non-local operators are handled separately.
They are Kaapana operators that start dedicated Kubernetes processing pods via the Kaapana Kubernetes runner.
In service workflows, a non-local operator can be forced to run in the services namespace by passing ``namespace=SERVICES_NAMESPACE`` to the corresponding ``KaapanaBaseOperator`` child, for example:

.. code-block:: python

    validate = DcmValidatorOperator(
        dag=dag,
        input_operator=get_input,
        exit_on_error=False,
        namespace=SERVICES_NAMESPACE,
    )

Airflow task logs are no longer collected by mounting a node-local log directory into every task pod.
Instead, when a task pod is created, the scheduler starts a best-effort log streamer for that pod.
The streamer reads logs from the Kubernetes pod log API and writes them into the regular Airflow log file layout.
If live streaming does not produce log content, a final non-following log fetch is used as a fallback.
This keeps logs available in the Airflow UI while allowing task pods to run in different namespaces without shared ``hostPath`` log mounts.

.. _preinstalled_dags:

Preinstalled DAGs
*******************

collect-metadata
""""""""""""""""""
This DAG collects metadata from the DICOM files in the selected dataset and stores it in the project bucket in MinIO.

import-niftis-from-data-upload
""""""""""""""""""""""""""""""""
This DAG converts NIfTI files to DICOM format and imports them into the internal PACS system.
More details can be found :ref:`here <import-uploaded-nifti-files>`.

delete-series
"""""""""""""""
This DAG deletes the all series in the dataset from the project.
If any series only belongs to the selected project, it will be deleted from the internal PACS system.
The option :code:`Delete entire study` allows to delete all series correspoding to each study in the dataset.

.. warning:: The option :code:`Delete entire study` might delete a series, even if it does not belong to the dataset.

download-selected-files
"""""""""""""""""""""""""""
.. warning:: This DAG is deprecated and will be removed in the future.

This DAG will create a zip file containing the series in the dataset and stores it in the project bucket in MinIO.

.. _evaluate-segmentations:

evaluate-segmentations
""""""""""""""""""""""""

This DAG is designed to compare two sets of segmentations, a ground truth and a prediction. All of the segmentations should be in the same dataset, the distinction between ground truth and test data is done via a :code:`test_tag`. More information about tagging data can be found in :ref:`datasets`. Note that you can either tag images manually, or use :code:`tag-dataset` workflow to apply to an entire dataset. 

Additionally, the DAG also contains a preprocessing step to fuse several annotation labels into a new unique label for better label specification. This fusion operation can be done for both the test data and the ground truth data.

As an example, let’s say you run a DAG like TotalSegmentator on CT data and get predicted segmentations. First, you can create a new test dataset with all new segmentations (by filtering for :code:`Series Description`, and more, to get all relevant segmentations and click on :code:`Save as Dataset`). Then you can go to this dataset and run :code:`tag-dataset` DAG. Now that all the predicted segmentations are tagged, you can create a new dataset with ground truth segmentations. After selecting this gt dataset, you can click on the :code:`Add to Dataset` button to add the test dataset on top of it.

1. Select the dataset that contains both test and gt segmentations. In the screenshot below, the predicted segmentations from TotalSegmentator are tagged with “pred”. 

.. image:: /img/eval-seg-1.png
   :alt: Tagging for segmentation evaluation
   :align: center

|

2. In the workflow form, fill in the parameters as follows:

.. image:: /img/eval-seg-2.png
   :alt: Segmentation evaluation form
   :width: 50%
   :align: center

a. **Evaluation metrics available**: select the metrics you want to run on the data. More details about the metrics can be found in `Monai Metrics docs <https://docs.monai.io/en/stable/metrics.html>`_ .
b. **Tag**: the tag that you use to separate ground truth from predictions, for this example we use :code:`pred`.
c. **Filter GT**: for filter operator, use :code:`Keep` or :code:`Ignore` to specify annotation labels that you want to filter in ground truth data. You can check the annotation labels of data by double clicking on them in Datasets view. Can also leave empty if you want to use all labels in the downstream operators.
d. **Filter Test Seg**: same with test data. Here we only select the ones we are interested in, because TotalSegmentator generates a lot of segmentations that are not useful for us in this case.
e. **GT Fuse Labels**: the label(s) that you want to fuse into a new label. In this example we are fusing :code:`lung` labels (each segmentation has two with same name)
f. **GT Fuse New Label Name**: the name of the new label created by fusing the labels above. :code:`lungsgt` for this example. Note that all the special characters will be removed from this label.
g. **Test Fuse Labels**: same with test data. In the example here we are fusing all the lung parts into a single “lungstest” label
h. **Test Fuse New Label Name**: same with test data
i. **Label Mappings**: in the format of :code:`gtlabelx:testlabely,gtlabelz:testlabelt`, include all the label mapping that you want to evaluate from GT and test data.

3. In Minio, the metrics.json file containing the results should be available under :code:`evaluate-segmentations` folder.

.. code-block::
   :caption: metrics.json

    {
        "1.2.276.0.7230010.3.1.3.17448391.39.1711634044.28207": {
            "dice_score": {
                "lungsgt:lungstest": [
                    0.9780710339546204
                ]
            },
            "surface_dice": {
                "lungsgt:lungstest": [
                    [
                        0.5737958550453186
                    ]
                ]
            },
            "hausdorff_distance": {
                "lungsgt:lungstest": [
                    [
                        25.475479125976562
                    ]
                ]
            },
            "asd": { // average surface distance
                "lungsgt:lungstest": [
                    [
                        0.44900786876678467
                    ]
                ]
            }
        },
        ...
    }


import-dicoms-from-data-upload
"""""""""""""""""""""""""""""""""""""""

This workflow expectes a zip file containing DICOM files as input.
The zip file must first be uploaded via the :ref:`Data Upload<data_upload>`.

The DAG will extract the zip file and send all DICOM files to the internal ctp server with selected project and the specified dataset name attached as :code:`--aetitle kp-<dataset-name> --call kp-<project-short-id>`.

The ctp server will trigger DAGs :ref:`service-process-incoming-dcm<service_process_incoming_dcm>`.

send-dicom
""""""""""""
This DAG can be used to send DICOM files to another DICOM receiver, e.g. to another Kaapana platform.

.. important::
    If you send data to another Kaapana platform, you have to specify the project as :code:`kp-<project-short-id>` and the dataset name as :code:`kp-<dataset-name>`.

service-daily-cleanup-jobs
"""""""""""""""""""""""""""
This DAG runs automatically every night to clean up the platform and perform the following tasks:
* :class:`kaapana.operators.LocalCleanUpExpiredWorkflowDataOperator` to delete workflow directories for expired workflows.
* :class:`kaapana.operators.LocalCtpQuarantineCheckOperator` to check the quarantine folder of the CTP and trigger :ref:`service-process-incoming-dcm<service_process_incoming_dcm>` if files were found.
* :class:`kaapana.operators.LocalServiceSyncDagsDbOperator` to synchronize the DAGs in the Airflow database with the DAGs in the file system.
* Clean old log files in the Airflow log directory.

.. _service_process_incoming_dcm:

service-email-send
"""""""""""""""""""
This dag consists only of the :class:`kaapana.operators.LocalEmailSendOperator`.


service-process-incoming-dcm
"""""""""""""""""""""""""""""
This DAG is triggered automatically whenever data is sent to the DICOM receiver of the platform.
It processes incoming DICOM data and performs the following tasks:

* Collect metadata from the DICOM files and store it the project index in OpenSearch. (This steps is also done for the _admin_ project.)
* Store the DICOM files in the internal PACS.
* Create series-project mappings for all incoming series to the associated project. (This steps is also done for the _admin_ project.)
* Generate thumbnails for all series and store them in MinIO. (This steps is also done for the _admin_ project.)
* Validate the DICOM files. Validation warnings and errors are stored as metadata and visible in the Gallery View. HTML reports are stored in MinIO. (This steps is also done for the _admin_ project.)
* Downstream DAGs will be triggered if specified for the :class:`kaapana.operators.LocalAutoTriggerOperator`.

service-re-index-dicom-data
"""""""""""""""""""""""""""""
This DAG can by triggered manually from the Airflow webinterface to repopulate the PACS, Opensearch, and the access-information-interface database from DICOM data stored on the file system.
This step can be helpful, when migrating from an older version of Kaapana to a newer one.

tag-dataset
""""""""""""

This DAG will add or remove tags from the series in the selected dataset.
The tags are stored in the OpenSearch index of the project and can be used to filter series in the Gallery View.

tag-seg-ct-tuples
""""""""""""""""""

This DAG expects a dataset of series with modalities _SEG_ or _RTSTRUCT_.
It will add the specified tags to all series in the dataset and corresponding reference series.
The tags are stored in the OpenSearch index of the project and can be used to filter series in the Gallery View.

tag-train-test-split-dataset
"""""""""""""""""""""""""""""

This DAG expexts a dataset of segmentation series.
It will split the dataset into a training and a test dataset based on the specified *Train split*.
Then it will tag all series of both splits according to the specified *Training tag* and *Test tag*.

validate-dicoms
""""""""""""""""

This DAG allows users to validate the DICOMS against the `DICOM standard <https://dicom.nema.org/medical/dicom/current/output/html/part01.html>`_. 
Currently this DAG allows one of the two algorithms to validate DICOMS: `dciodvfy` and `dicom-validator`. 
Validation results are stored in MinIO as a result file. The DAG runs each time data is imported into the platform.

clear-validation-results
""""""""""""""""""""""""""
This DAG can be used to clear the validation result from the Dataset.
