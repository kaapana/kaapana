.. _user_guide:

User guide
==========
This manual is intended to provide a quick and easy way to get started with :term:`kaapana`.
This project should not be considered a finished platform or software. 

Sending images to the platform and appling a processing pipeline to the imates
----------------------------------------------------------------------------

Triggering workflows with Kibana
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
As mentioned above, Kibana visualizes all the metadata of the images and is therefore a good option to also filter the images to which a workflow should be applied. To trigger a workflow from Kibana, a panel 'send_cohort' was added to the Kibana dashboard which contains a dropdown to select a workflow, the option between single and batch file processing and a send button, which will send the request to Airflow.

Single and batch file processing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The difference between single and batch file processing is that in single file processing for every image an own DAG is triggered. Therefore, each operator within the DAG only obtains a single image at a time. When selecting batch file processing, for all the selected images only one DAG is started and every operator obtains all images in the batch. In general, batch file processing is recommended. Single file processing is only necessary if an operator within the workflow can only handle one image at a time.

Handling of the Kibana request to provide PACS images for the upcoming workflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Once Kibana has sent its request to the custom Airflow API, we use the query of Kibana to download the selected images from the local PACS system DCM4CHEE to a predefined directory in the local file system so that the images are available for the upcoming workflow.

Airflow: DAGs, operators and the UI in action
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This section will introduce a basic DAG as well as the usage of the UI to examine a running DAG and its operators. As an example DAG, let us take a look at the 'download-selected-files' workflow. This can be done via the UI of Airflow. First, go to Airflow and then click on the 'download-selected-files' DAG. Now you should see the 'Graph View' of the DAG which shows the two operators of the pipeline. On the same level as the 'Graph View' tab, a tab called 'Code' is available, which shows the code of the DAG. After importing the necessary dependencies, a DAG object is created which contains, among other things, the id of the DAG (its name). Then, the two operators objects are created. The ``LocalPushFiles2MinioOperator`` will push the files to Minio. The last line of the DAG defines the pipeline, therefore, the ``LocalPushFiles2MinioOperator`` is executed.

To see the DAG in action, go to the Kibana dashboard, select a few images and trigger the DAG 'download-selected-files' with the batch file processing option. Once you have triggered the workflow, go to the main page of Airflow. As mentioned above, the images get first downloaded from the local PACS and are saved to a directory called ``initial-input`` within the workflows folder on the server. This is done by a different DAG called 'processing_incoming_elastic'. You will see that this DAG is working right now. The colored circles in the 'Recent Tasks' section indicate the current status of the operators. The 'processing_incoming_elastic' DAG will trigger then the 'download-selected-files' DAG. If you go to the 'Graph View' of the 'download-selected-files' DAG, you will see how the operators also get colored. By clicking on an operator, a small window opens where you can click, for example, on 'View Log' to see the output of the operator. This is very helpful to debug an operator.

Kubernetes to manage processing Docker containers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If an operator does not run in pure Python but triggers a Docker container instead, the container will be managed by Kubernetes. In Kubernetes, a namespace called 'flow-jobs' is reserved for all processing containers. If you select this namespace in the dashboard, you will see all the containers which were triggered by Airflow. E.g. the 'organ-segmentation' DAG triggers Docker containers. Also, Kubernetes will be helpful for debugging a Docker container.


Debugging
-------------------------------------------------
This short section will show you how to debug in case a workflow throws an error.

**Syntax errors**:

If there is a syntax error in the implementation of a DAG or in the implementation of an operator, the errors are normally shown directly at the top of the Airflow DAGs view in red. For further information, you can also consult the log of the container that runs Airflow. For this, you have to go to Kubernetes, select the namespace 'flow' and click on the Airflow pod. On the top right there is a button to view the logs. Since Airflow starts two containers at the same time, you can switch between the two outputs at the top in 'Logs from…'.

**Operator errors during execution**:

* Via Airflow: when you click in Airflow on the DAG you are guided to the 'Graph View'. Clicking on the red, failed operator a popup opens where you can click on 'View Log' to see what happened.
* Via Kubernetes: in the namespace flow-jobs, you should find the running pod that was triggered from Airflow. Here you can click on the logs to see why the container failed. If the container is still running, you can also click on 'Exec into pod' to debug directly into the container.

After you resolved the bug in the operator, you can either restart the whole workflow from Kibana or you can click on the operator in the 'Graph View', select 'Clear' in the popup and confirm the next dialog. This will restart the operator.


Behind the scence: Concepts and technology stack for large-scale image processing
---------------------------------------------------------------------------------

This section gives an overview of the technologies that are implemented to make large-scale image processing possible. The first section will explain where data are stored within the platform and the second part will introduce how processing pipelines are realized within the platform.

Core stack: Kubernetes, Traefik, Louketo
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Comments about the core stack

Storage stack: Kibana, Elasticsearch and DCM4CHEE
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When DICOMs are sent to the DICOM receiver of the platform two things happen. Firstly, the DICOMs are saved in the local PACs system called DCM4CHEE. Secondly, the meta data of the DICOMs are extracted and indexed by a search engine (powered by Elasticsearch) which makes the meta data available for Kibana. Kibana is mainly responsible for visualizing the metadata but it also serves as a filter to select images and to trigger a processing pipeline on the selected images. Images in Kibana (meta dashboard) can be selected via custom filters at the top. To ease this process, it is also possible to add filters automatically by clicking on the graphs.

In general, data that are in the DICOM format should be stored in the DCM4CHEE PACS. Since some processing pipelines might generate data that are not DICOMs, an object store called Minio is available. In Minio, data are stored in buckets and are accessible via the GUI for download.

If you are more interested in the technologies, you can get started here:

* `Kibana <https://www.elastic.co/guide/en/kibana/current/getting-started.html>`_
* `Elasticsearch <https://www.elastic.co/guide/en/elasticsearch/reference/current/elasticsearch-intro.html>`_

Processing stack: Airflow, Kubernetes namespace 'flow-jobs' and the working directory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order to apply processing pipelines in which different operations are performed in a certain order to images, a framework is necessary which allows us to define and trigger such a pipeline. We decided to use Airflow for that. In Airflow, a workflow is called a DAG (directed acyclic graph, a graph type where you can only traverse forwards). It consists of operators which are the bricks of your pipeline. Ideally, every operator triggers a Docker container in which some kind of task is performed. A detailed overview of the concepts can be found `here <https://airflow.apache.org/docs/stable/concepts.html>`_.

Besides Airflow, Kubernetes is used to manage the Docker containers that are triggered by Airflow. On the platform, we introduce a namespace called 'flow-jobs' in which all containers initiated by Airflow are started.

Finally, we are introducing the working directory of Airflow which should be in the ``data`` directory of the platform in a folder called ``workflows`` (e.g. ``/home/kaapana/workflows)`` in which three other directories appear:

* The ``dags`` directory is the place where all DAGs and most of the operators are defined.
* The ``plugins`` directory contains the kaapana plugin that was written by us. Here we define some basic operators, the connection to Kubernetes as well as an own API to communicate with Airflow. It is for example used to trigger a DAG externally or to get an overview over existing workflows.
* The ``data`` directory is the place where all the data that are generated during a pipeline are temporarily stored.

If you are more interested in the technologies, you can get started here:

* `Airflow <https://airflow.apache.org/docs/stable/tutorial.html>`_
* `Kubernetes <https://kubernetes.io/docs/concepts/>`_
