.. _airflow:

Airflow
^^^^^^^^^^

In Airflow, we define Directed Acyclic Graphs (DAGs) that build our data-processing pipelines.
These DAGs are composed of multiple operators, each serving a specific task.
Within Kaapana, we categorize operators into two types: `Local` operators and `containerized` operators.
Local operators are executed within the `airflow-scheduler` container.
On the other hand, when a `containerized` operator is triggered, a dedicated Kubernetes job is spawned, encapsulating a container responsible for executing the operator's code.
We commonly refer to these containers as `processing-containers`.

Furthermore, Airflow functions as the scheduling system for the data-processing-pipelines.
The Airflow user interface offers comprehensive insights into DAGs, DAG runs, and their scheduling details.

The platform comes with several DAGs that can be used for data-management.
Additional DAGs can be installed as `ẁorkflow-extensions` in the `Extensions` page.

collect-metadata
******************

convert-niftis-to-dicom-and-import-to-pacs
********************************************

delete-series-from-platform
******************************

download-selected-files
***************************

evaluate-segmentations
************************

import-dicoms-in-zip-to-internal-pacs
***************************************

send-dicom
************

service-daily-cleanup-jobs
***************************

service-extract-metadata
***************************

service-process-incoming-dcm
*****************************

service-re-index-dicom-data
*****************************

service-segmentation-thumbnail
********************************

tag-dataset
************

tag-seg-ct-tuples
******************

tag-train-test-split-dataset
*****************************

train-with-pretrained-weights
*******************************