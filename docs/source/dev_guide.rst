Technology stack for large-scale image processing
=================================================

This section gives an overview of the technologies that are implemented to make large-scale image processing possible. The first section will explain where data are stored within the platform and the second part will introduce how processing pipelines are realized within the platform.

Storage stack: Kibana, Elasticsearch and DCM4CHEE
-------------------------------------------------

When DICOMs are sent to the DICOM receiver of the platform two things happen. Firstly, the DICOMs are saved in the local PACs system called DCM4CHEE. Secondly, the meta data of the DICOMs are extracted and indexed by a search engine (powered by Elasticsearch) which makes the meta data available for Kibana. Kibana is mainly responsible for visualizing the metadata but it also serves as a filter to select images and to trigger a processing pipeline on the selected images. Images in Kibana (meta dashboard) can be selected via custom filters at the top. To ease this process, it is also possible to add filters automatically by clicking on the graphs.

In general, data that are in the DICOM format should be stored in the DCM4CHEE PACS. Since some processing pipelines might generate data that are not DICOMs, an object store called Minio is available. In Minio, data are stored in buckets and are accessible via the GUI for download.

If you are more interested in the technologies, you can get started here:

* `Kibana <https://www.elastic.co/guide/en/kibana/current/getting-started.html>`_
* `Elasticsearch <https://www.elastic.co/guide/en/elasticsearch/reference/current/elasticsearch-intro.html>`_

Processing stack: Airflow, Kubernetes namespace 'flow-jobs' and the working directory
-------------------------------------------------------------------------------------

In order to apply processing pipelines in which different operations are performed in a certain order to images, a framework is necessary which allows us to define and trigger such a pipeline. We decided to use Airflow for that. In Airflow, a workflow is called a DAG (directed acyclic graph, a graph type where you can only traverse forwards). It consists of operators which are the bricks of your pipeline. Ideally, every operator triggers a Docker container in which some kind of task is performed. A detailed overview of the concepts can be found `here <https://airflow.apache.org/docs/stable/concepts.html>`_.

Besides Airflow, Kubernetes is used to manage the Docker containers that are triggered by Airflow. On the platform, we introduce a namespace called 'flow-jobs' in which all containers initiated by Airflow are started.

Finally, we are introducing the working directory of Airflow which should be in the ``data`` directory of the platform in a folder called ``workflows`` (e.g. ``/home/kaapana/workflows)`` in which three other directories appear:

* The ``dags`` directory is the place where all DAGs and most of the operators are defined.
* The ``plugins`` directory contains the kaapana plugin that was written by us. Here we define some basic operators, the connection to Kubernetes as well as an own API to communicate with Airflow. It is for example used to trigger a DAG externally or to get an overview over existing workflows.
* The ``data`` directory is the place where all the data that are generated during a pipeline are temporarily stored.

If you are more interested in the technologies, you can get started here:

* `Airflow <https://airflow.apache.org/docs/stable/tutorial.html>`_
* `Kubernetes <https://kubernetes.io/docs/concepts/>`_

Understand the concepts of how workflows are triggered, supervised and debugged
===============================================================================

Triggering workflows with Kibana
--------------------------------
As mentioned above, Kibana visualizes all the metadata of the images and is therefore a good option to also filter the images to which a workflow should be applied. To trigger a workflow from Kibana, a panel 'send_cohort' was added to the Kibana dashboard which contains a dropdown to select a workflow, the option between single and batch file processing and a send button, which will send the request to Airflow.

Single and batch file processing
--------------------------------
The difference between single and batch file processing is that in single file processing for every image an own DAG is triggered. Therefore, each operator within the DAG only obtains a single image at a time. When selecting batch file processing, for all the selected images only one DAG is started and every operator obtains all images in the batch. In general, batch file processing is recommended. Single file processing is only necessary if an operator within the workflow can only handle one image at a time.

Handling of the Kibana request to provide PACS images for the upcoming workflow
-------------------------------------------------------------------------------
Once Kibana has sent its request to the custom Airflow API, we use the query of Kibana to download the selected images from the local PACS system DCM4CHEE to a predefined directory in the local file system so that the images are available for the upcoming workflow.

Introducing the underlying folder structure
-------------------------------------------
A DAG in Airflow is constructed of operators and somehow data must be transferred between them. To standardize the way data are stored on the local file system, we introduced a fixed folder structure. We are using a temporary directory called ``data`` inside the Airflow folder (e.g. ``/home/kaapana/workflows``), where all data that are generated during a workflow are saved. It is normally part of the workflow to clean this data after everything finished.

.. note::
   The ``data`` directory and its files are also accessible on the landing page of the platform. You get there via the tab 'System' → 'Workflow-data'.

Within the ``data`` directory, every DAG that is started generates a folder with its ``dag_id``. Coming back to single and batch file processing this means that in the case of single file processing for each image a separated ``dag_id`` folder is created whereas for batch file processing only one ``dag_id`` folder is used.

Within the ``dag_id`` folder, all data concerning the DAG will be saved. Here, we make a separation between data that are created or belong to a whole batch of images and data that are specific for each image. For image specific data, another folder called ``batch`` (set by a global Python variable ``BATCH_NAME``) is introduced which contains folders named by the DICOM series-ids. Therefore, the series id of the DICOM serves as an identifier within the batch folder. The final folder layer is the layer of the output of each operator. Thus, if an operator generates data, those are stored within a folder with the name of the operator. This is done similar for image specific and batch data. Images that are downloaded from Kibana are per default located in a directory called ``initial-input`` (set by a global Python variable ``INITIAL_INPUT_DIR``) within the series-id folder of each image. Given this folder structure, it will be very easy to handle the data transfer between operators. Here is an example of a folder structure of an example workflow:

.. literalinclude:: ../../../../workflows/tutorial/scripts-and-folders/data_folder_structure.txt

Airflow: DAGs, operators and the UI in action
---------------------------------------------
This section will introduce a basic DAG as well as the usage of the UI to examine a running DAG and its operators. As an example DAG, let us take a look at the 'download-selected-files' workflow. This can be done via the UI of Airflow. First, go to Airflow and then click on the 'download-selected-files' DAG. Now you should see the 'Graph View' of the DAG which shows the two operators of the pipeline. On the same level as the 'Graph View' tab, a tab called 'Code' is available, which shows the code of the DAG. After importing the necessary dependencies, a DAG object is created which contains, among other things, the id of the DAG (its name). Then, the two operators objects are created. The ``LocalPushFiles2MinioOperator`` will push the files to Minio. The last line of the DAG defines the pipeline, therefore, the ``LocalPushFiles2MinioOperator`` is executed.

To see the DAG in action, go to the Kibana dashboard, select a few images and trigger the DAG 'download-selected-files' with the batch file processing option. Once you have triggered the workflow, go to the main page of Airflow. As mentioned above, the images get first downloaded from the local PACS and are saved to a directory called ``initial-input`` within the workflows folder on the server. This is done by a different DAG called 'processing_incoming_elastic'. You will see that this DAG is working right now. The colored circles in the 'Recent Tasks' section indicate the current status of the operators. The 'processing_incoming_elastic' DAG will trigger then the 'download-selected-files' DAG. If you go to the 'Graph View' of the 'download-selected-files' DAG, you will see how the operators also get colored. By clicking on an operator, a small window opens where you can click, for example, on 'View Log' to see the output of the operator. This is very helpful to debug an operator.

Kubernetes to manage processing Docker containers
-------------------------------------------------
If an operator does not run in pure Python but triggers a Docker container instead, the container will be managed by Kubernetes. In Kubernetes, a namespace called 'flow-jobs' is reserved for all processing containers. If you select this namespace in the dashboard, you will see all the containers which were triggered by Airflow. E.g. the 'organ-segmentation' DAG triggers Docker containers. Also, Kubernetes will be helpful for debugging a Docker container.

Debugging
---------
This short section will show you how to debug in case a workflow throws an error.

**Syntax errors**:

If there is a syntax error in the implementation of a DAG or in the implementation of an operator, the errors are normally shown directly at the top of the Airflow DAGs view in red. For further information, you can also consult the log of the container that runs Airflow. For this, you have to go to Kubernetes, select the namespace 'flow' and click on the Airflow pod. On the top right there is a button to view the logs. Since Airflow starts two containers at the same time, you can switch between the two outputs at the top in 'Logs from…'.

**Operator errors during execution**:

* Via Airflow: when you click in Airflow on the DAG you are guided to the 'Graph View'. Clicking on the red, failed operator a popup opens where you can click on 'View Log' to see what happened.
* Via Kubernetes: in the namespace flow-jobs, you should find the running pod that was triggered from Airflow. Here you can click on the logs to see why the container failed. If the container is still running, you can also click on 'Exec into pod' to debug directly into the container.

After you resolved the bug in the operator, you can either restart the whole workflow from Kibana or you can click on the operator in the 'Graph View', select 'Clear' in the popup and confirm the next dialog. This will restart the operator.


Writing your own workflow
=========================

Setting up your development environment:
----------------------------------------

First of all, we need to setup an environment where it is easy to develop and test DAGs as well as to create own Docker containers. For the DAGs and operator development there are the following three different ways possible. For Docker container creation you need to have Docker installed on your system.

.. note::
    In order to write your own Docker container, you need to have Docker `installed on your machine <https://docs.docker.com/install/>`_.

.. note::
    All files that are shown in this document can also be downloaded with:
    ::
        curl -L -O https://jip.dktk.dkfz.de/42fef1/files/development_guide_files.zip

.. hint::
    We suggest to use a dedicated server for the development of DAGs and operators. You can install the platform as written in the    :ref:`Installation guide <pi_index_doc>`.

**1. Visual Studio Code**

With Visual Studio Code, you can directly connect from your local machine via ssh to the workflows folder of the server where your platform is running. Make sure you have Visual Studio Code `installed on your machine <https://code.visualstudio.com/docs/setup/setup-overview>`_.

In order to have read and write access from Visual Studio Code, we suggest to perform the following steps on your server.

.. literalinclude:: ../../../../workflows/tutorial/scripts-and-folders/change_permissions.txt
   :language: bash

Please follow the instructions below to connect via SSH to the server:

1. Make sure you have ssh access to the server
2. Install Remote-SSH Extension vor Visual Studio Code (Ctrl+Shift+X -> search for Remote - SSH _> select install)
3. Add an alias to your SSH config file on your local machine (``/home/USERNAME/.ssh/config``)

::

    Host kaapana-dev
    User <user>
    HostName <host>
    IdentityFile path/to/your/private/pem # Or leave empty if you log in via password

4. Connect to the server from Visual Studio Code

    1. Press ``F1`` and select ``Remote-SSH: Connect to Host``
    2. Enter ``<user>@<host>`` or ``<kaapana-dev>``

When you connected successfully, open the workflows folder. Here, you should see the already written DAGs and operators in your Visual Studio Code instance.

**2. Theia-ide**

Eclipse Theia is an IDE which can be deployed in the cloud so that we can access the workflows directory directly via the browser. To deploy the IDE, you need to install the web-ide helm chart. This can be done with:

::

    helm init --client-only
    helm repo add --username '<user credentials for repository>' tutorial https://dktk-jip-registry.dkfz.de/chartrepo/tutorial
    helm install --name theia-ide --version 1.0-vdev tutorial/theia-ide

where you should use the credentials that were provided to you to access our Docker registry.

.. note::
   In case you want to remove the web-ide again, you can delete the package again with:
   ::

        helm delete --purge theia-ide

The helm package will automatically change the permissions of the workflows folder. If you cannot edit the files for some reason, you might need to restart the pod by going to Kubernetes and deleting the 'theia-ide' pod in the default namespace or change the file permission manually as described in the Visual Studio Code section.

After the pod is ready, you can access the IDE via ``http://YOUR_SERVER_ADDRESS/web-ide/``. Make sure that you have access to the dags folder and that you can create and edit files.

**3. Via Vim or Nano**

Of course, you can also directly log into the server and edit the files with Vim or Nano.

Concepts of DAGs, operators and docker containers
-------------------------------------------------

**DAGs and operators**

As mentioned above, a workflow defined by a DAG imposes an order on the operators which in turn perform some processing steps on a dataset. The platform itself comes with some predefined DAGs which you can find in the directory ``<workflows-folder>/dags``. Furthermore, we have implemented a basic stack of operators that perform common operations like pushing files to Minio. You find these operators in ``<workflows-folder>/plugins/kaapana/operators``.

**KaapanaBaseOperator**

Since all DAGs and operators should live in harmony with the existing DAGs and operators, we introduced a base class called ``KaapanaBaseOperator.py`` (``<workflows-folder>/plugins/kaapana/operators/KaapanaBaseOperator.py``) that should be used when writing an operator that starts a Docker container. It takes care of some important tasks which you normally do not need to worry about like the Docker deployment on the Kubernetes cluster, mounting of file systems or definition of default values. In case you write an operator that does not launch a Docker container but runs locally in the Python environment of Airflow, we provide the ``kaapanaPythonBaseOperator.py``, however, we strongly recommend to only write operators that launch a Docker container.

Here, a short overview of the most important parameters of the ``KaapanaBaseOperator``:

* ``dag``: The dag object to which the operator belongs to
* ``name``: The name of the operator
* ``image``: The Docker image that should be launched from the operator
* ``input_operator``: An operator object of which the called operator needs the output data
* ``operator_out_dir``: The relative directory, where the operator should write its output data. Per default it is set to the name the task_id of the operator, which is per default the name of the operator
* ``env_vars``: A dict of environment variables that you like to give to the launched Docker container. Per default the following variables are set, they will help to easily find locate the data within the Docker container
* ``image_pull_secrets``: The docker registry secret that should be used to download the image from the dedicated registry

Here, a few words of some default values that are set in the constructor of KaapanaBaseOperator:

* ``WORKFLOW_DIR``: The directory, where the data are mounted to in an container. Default to ``data``
* ``BATCH_NAME``: The name of the batch folder within a DAG. Default to ``batch``
* ``INITIAL_INPUT_DIR``: The name of the folder where operators look at, if no ``operator_in_dir`` is set. Default to ``initial-input`` 
* ``operator_out_dir``: This variable defines the relative directory of where the data is written to, it is set by default to the name of the operator. This helps an upcoming operator to know where to look for data from the previous operator
* ``operator_in_dir``: This variable defines the relative location of the data with which the operator should work with. If no ``operator_in_dir`` is set, it falls back to the ``INITIAL_INPUT_DIR``. This is the subdirectory where the DICOM images are moved to when a workflow is triggered via the Kibana dashboard. Otherwise it is set per default to the operator_out_dir of an input_operator


**Operator and Docker container templates**

In the following, we will present some templates that you can adapt when writing your own operators and Docker containers. They also illustrate how the environmental variables that are set in the ``KaapanaBaseOperatory`` are supposed to be used within a Docker container.

First of all an operator template that launches a Docker container. Since often you need to add additional environment variables to a container, we added here as an example an additional environment variable to describe the relative output directory of another operator ``TemplateOperator.py``:

.. literalinclude:: ../../../../workflows/tutorial/templates/dags/tutorial/TemplateOperator.py

Secondly, a generic way of how to create own Docker images. In one example a Python script is executed within the Docker container, in the other example a Bash script is executed. Let us start with the Bash script example. When we write a Docker container, we generally use the following folder structure:

.. literalinclude:: ../../../../workflows/tutorial/scripts-and-folders/folder_structure_docker.txt

The ``files`` directory contains all files which should be copied to the Docker container. In this case, only the ``process.sh`` file.
The ``Dockerfile`` itself takes the ``nvidia/cuda:10.0-runtime-ubuntu18.04`` as base image, copies the ``process.sh`` file to the Container and finally executes the bash script. For overview purposes, we always add the name of the docker registry, the name of the repository, the name of the image and its version to the docker file.

In the ``process.sh`` file, it is shown how we generally perform operations on the input data and to which location we write the output data. At the top, you can see how to work on individual images and on the bottom how to work with the whole batch.

.. literalinclude:: ../../../../workflows/tutorial/templates/docker-container/DockerBashTemplate/files/process.sh
   :language: bash

When we want to execute a simple Python script, we need to adapt the ``Dockerfile`` as follows:

.. literalinclude:: ../../../../workflows/tutorial/templates/docker-container/DockerPythonTemplate/Dockerfile

In the ``process.py`` file we basically perform the same steps as above.

.. literalinclude:: ../../../../workflows/tutorial/templates/docker-container/DockerPythonTemplate/files/process.py

As a first example of building our own workflow, we will execute the two Docker images.

**Communication with our Docker registry**

Since the whole platform is based on Docker images, we established a dedicated Docker registry for all the Docker images.
If you have docker installed, you can log in to our Docker registry with:

::

    docker login dktk-jip-registry.dkfz.de

Each DKTK site has received its own credentials. If you do not have credentials, please contact the kaapana team. For this tutorial, we have created a project called 'tutorial' on our docker registry to which you can push the containers from this tutorial. However, we ask you to add your institution name in the version tag (e.g. ``<your-institution>-1.0``). In case you need your own project for your Docker images, you can contact us.

Here is an example of how to build an own Docker image:
::

    docker build -t dktk-jip-registry.dkfz.de/tutorial/bash-template:dkfz-1.0 .

Finally, you can push a container like this:
::

    docker push dktk-jip-registry.dkfz.de/tutorial/bash-template:dkfz-1.0

Hands-on creating workflows
---------------------------

.. note::
    Before we can start you need to send some images to the platform since the **default test-image** that we send to the server **will not work** for the workflows. How you can do this as explained in the :ref:`FAQ <send_images_to_the_platform_doc>`.

**1. Play with the templates**

In the first example, we will simply execute the two template operators and afterwards clean the workflow directory. We start with the two operators ``TemplateExecBashOperator.py`` and ``TemplateExecPythonOperator.py``, which we want to execute:

.. literalinclude:: ../../../../workflows/tutorial/templates/dags/tutorial/TemplateExecBashOperator.py

.. literalinclude:: ../../../../workflows/tutorial/templates/dags/tutorial/TemplateExecPythonOperator.py

Then, we define the dependencies in the DAG and also add the cleaning operator ``dag_template_showcase.py``.


.. literalinclude:: ../../../../workflows/tutorial/templates/dags/dag_template_showcase.py

In order to include the DAG and operators into your platform, you need to copy all files into the ``dag`` directory of the ``workflows`` folder according to the following folder structure:

.. literalinclude:: ../../../../workflows/tutorial/scripts-and-folders/template_folder_structure.txt

After a few minutes, Airflow as well as Kibana will recognize the new DAG.

.. note::
   If the DAG is not recognized, it is sometimes necessary to restart Airflow. This can be done via Kubernetes by selecting the namespace 'flow' from the dropdown menu and then by deleting the Airflow pod. (In rare cases you might also need to delete the database file of postgres-airflow on your file-system (``<jip-directory>/data/postgres-airflow``) and restart in addition to Airflow also the Postgres Airflow pod.)

After the DAG is correctly recognized by Airflow, you can trigger it by selecting at least one DICOM image on the Kibana dashboard and run the 'template-showcase' with batch or single file processing.

Take a look into the log of the operators; it will print out the directories of your files.

**2. Workflow to convert DICOM to ``.nrrd``**

In this example, we would like to convert DICOMs to ``.nrrd`` and push the resulting ``.nrrd`` file to Minio so that it is available for download. The DAG ``dag_dcm2nrrd.py`` is defined as follows:

.. literalinclude:: ../../../../workflows/tutorial/examples/dags/dag_dcm2nrrd.py

Here, we added an operator that pushes the generated ``.nrrd`` files to Minio. This operator gets the ``DcmConverterOperator`` object as input so that it knows which data to push. With the ``file_white_tuples`` variable we specify that only ``.nrrd`` files are uploaded to Minio.

Copy the file again to the ``dags`` directory and you are ready to convert DICOMs to ``.nrrd`` files. Once the workflow ran successfully, you should see a bucket named  ``dcm2nrrd`` on Minio which contains the ``.nrrd`` files.

**3. Create an operator that extracts the study-ids**

The aim of this operator is to extract the ``study_id`` of a DICOM and write it to a JSON file. We simply copy the ``template-operator`` from above and adapt some variables so that we get the ``ExtractStudyIdOperator.py``:

.. literalinclude:: ../../../../workflows/tutorial/examples/dags/examples/ExtractStudyIdOperator.py

Let us integrate the operator into a DAG ``dag_extract_study_id.py``:

.. literalinclude:: ../../../../workflows/tutorial/examples/dags/dag_extract_study_id.py

Next, we need to build the docker image ``extract-study-id:dkfz-1.0``. For this, we take the Python example template from above (remember to adapt the institution in the version name). Instead of the ``process.py`` file we use a file called ``extract_study_id.py``

.. literalinclude:: ../../../../workflows/tutorial/examples/docker-container/extract-study-id/files/extract_study_id.py

Furthermore, we introduce a ``requirements.txt`` file where we save the Python dependencies:

.. literalinclude:: ../../../../workflows/tutorial/examples/docker-container/extract-study-id/files/requirements.txt

Finally, we need to adapt the ``Dockerfile`` to:

.. literalinclude:: ../../../../workflows/tutorial/examples/docker-container/extract-study-id/Dockerfile

Once we adapted all files, we need to build and push the docker image:

::

    docker build -t dktk-jip-registry.dkfz.de/tutorial/extract-study-id:dkfz-1.0  .
    docker push dktk-jip-registry.dkfz.de/tutorial/extract-study-id:dkfz-1.0

Finally, copy the DAG and the operator and test the workflow on some DICOM images.

**4. Creating an operator that saves batch-specific information**

In the example above, the operator generates for each image a json file. However, there are also cases where we are interested in pooled information from all the images. Therefore, this short add-on will show you how to concatenate the output of the previous operator into a single file.

The operator which calls the corresponding Docker image ``PoolJsonsOperator.py``:

.. literalinclude:: ../../../../workflows/tutorial/examples/dags/examples/PoolJsonsOperator.py

And the DAG ``dag_pool_study_ids.py``:

.. literalinclude:: ../../../../workflows/tutorial/examples/dags/dag_pool_study_ids.py

Next the ``Dockerfile``:

.. literalinclude:: ../../../../workflows/tutorial/examples/docker-container/pool-jsons/Dockerfile

And the processing script ``pool_jsons.py``:

.. literalinclude:: ../../../../workflows/tutorial/examples/docker-container/pool-jsons/files/pool_jsons.py


Finally, build and push the Docker images and test the workflow on some DICOM images.
  
**5. Creating a more complicated workflow**

This final example will show a more sophisticated workflow. Let us say we have a workflow where we need to execute the same operator multiple times. Since per default the files are written to a directory named after the operator, we introduced a variable called ``parallel_id`` that can be added in the constructor of the operator and is appended to the directory name so that each operator writes to a unique directory.

A simple, however, non-sensible example DAG ``dag_extract_multiple_study_ids.py`` looks like this:

.. literalinclude:: ../../../../workflows/tutorial/examples/dags/dag_extract_multiple_study_ids.py

Finally, you can learn a lot more about how to write DAGs, operators and how to use the existing operators by taking a look at the DAGs and operators that are deployed with the installation of the platform.

**6. How to remove the DAGs**:

Removing your DAGs from Airflow can done in two steps:

* Delete the DAG from the directory on your server
* Delete the DAG from the Airflow UI.
