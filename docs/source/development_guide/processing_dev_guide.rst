.. _processing_dev_guide:

Processing Dev-Guide
====================

Introduction
------------

Write your first own DAG
^^^^^^^^^^^^^^^^^^^^^^^^

**Aim**: Create a DAG that converts DICOMs to ``.nrrd`` files

In order to deploy now a new DAG that convert DICOMs to nrrds, create a file called ``dag_example_dcm2nrrd.py`` inside the ``dags``-folder with the following content:

.. literalinclude:: ../../../templates_and_examples/examples/workflows/airflow-components/dags/dag_example_dcm2nrrd.py
    
That's it basically. Now we can check if the DAG is successfully added to Airflow and then we can test our workflow!

* Go to Airflow and check if your newly added DAG ``example-dcm2nrrd`` appears under DAGs (it might take up to five minutes that airflow recognizes the DAG! Alternatively you could restart the Airflow Pod in Kubernetes)
* If there is an error in the created DAG file like indexing, library imports, etc, you will see an error at the top of the Airflow page
* Go to the Meta-Dashboard 
* Filter via the name of your dataset and with ``+/-`` icons on the different charts your images to which you want to apply the algorithm 
* From the drop-down, choose the DAG you have created i.e. ``example-dcm2nrrd`` and press the start button. In the appearing pop-up window press start again and the execution of your DAG is triggered.
* In order to check if your DAG runs successfully, you can go back to Airflow and watch how the pipeline jumps from one operator to the next. If an error occurs please check out the TODO section.
* If everything was successful you can go to Minio where you will find a bucket called ``example-dcm2nrrd``. Inside this folder you will find the ``.nrrd`` files of the selected images.

.. _Deploy an own processing algorithm to the platform:

Deploy an own processing algorithm to the platform
--------------------------------------------------

**Aim:** We will write a workflow that opens a DICOM file with Pydicom, extracts the study id, saves the study id in a json file and pushes the json file to Minio.

Step 1: Check if our scripts works locally
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
First of all, it is important that your script works. For this, we will simulate the folder structure that we expect on the platform and apply our algorithm locally to the files. In order to simulate the folder structure. Please go back to the Meta-Dashboard, select the files you want to develop with and trigger the DAG ``download-selected-files`` with option zip files ``False``. This will download the selected images to a folder in Minio. Please go to Minio, download the folder called ``batch`` and save the extracted content to a folder called ``data``. Now the ``data`` folder corresponds to the ``data`` folder that you have seen in the workflows folder.

.. hint::

  | In case your algorithm works with ``.nrrd`` files you could simply download the batch folder that we generated in the example-dcm2nrrd folder

* Now we create the following python script ``extract_study_id.py``. Make sure that we have Pydicom installed:

.. literalinclude:: ../../../templates_and_examples/examples/workflows/processing-container/extract-study-id/files/extract_study_id.py

.. hint::

  | When creating a new algorithm you can always take our templates (``templates_and_examples/templates/processing-container``) as a starting point and simply add your code snippet in between for the processing.

In order to test the script we uncomment the os.environ sections and adapt the ``WORKFLOW_DIR`` to the ``data`` location on our local file system. Then we execute the script. On the platform all the environment variables will be set automatically. If the algorithm runs without errors, the most difficult part is already done, we have a running workflow!

Step 2: Check if our scripts runs inside a Docker container
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The next step is to put the algorithm into a Docker container and test if everything works as expected. For this we will put the ``extract_study_id.py`` in a folder called ``files``, comment again the os.environ section and create the following file called ``Dockerfile`` next to the files directory:

.. literalinclude:: ../../../templates_and_examples/examples/workflows/processing-container/extract-study-id/Dockerfile

The Dockerfile basically copies the python script and executes it.

.. hint::

  | Also here you can take our templates as a starting point.

In order to build and test the Dockerfile and the resulting container proceed as follows:

* Build the docker container by executing:

::

   sudo docker build -t <docker-registry><docker-repo>/example-extract-study-id:0.1.0 .

.. hint::

  | Depending on your docker registry ``docker-repo`` might be not defined: ``docker-repo=''`` or the name of the docker repository!

* Run the docker image, however, specify the environment variable as well as mount your local file system into the Docker container to a directory called data. This mount will also be made automatically on the platform.

::

   sudo docker run -v <directory with the data folder>:/data -e WORKFLOW_DIR='data' -e BATCH_NAME='batch' -e OPERATOR_IN_DIR='dcm-converter' -e OPERATOR_OUT_DIR='segmented-nrrd'  <docker-registry><docker-repo>/example-extract-study-id:0.1.0


In order to debug directly into the container you can execute:

::

   sudo docker run -v <directory with the data folder>:/data -e WORKFLOW_DIR='data' -e BATCH_NAME='batch' -e OPERATOR_IN_DIR='dcm-converter' -e OPERATOR_OUT_DIR='segmented-nrrd'  -it <docker-registry><docker-repo>/example-extract-study-id:0.1.0 /bin/sh

* Finally you need to push the docker container to make it available for the workflow

If not already done, log in to the docker registry:

::

   sudo docker login <docker-registry>

and push the docker image with:
::

   sudo docker push <docker-registry><docker-repo>/example-extract-study-id:0.1.0


Step 3: Create a DAG and Operator for the created Docker container
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Now, we will embed the created Docker container into an operator that will be part of an Airflow DAG.

* Go again to the code-server ``/code``
* Create a folder called ``example`` inside the ``dags`` directory
* Create a file called ``ExtractStudyIdOperator.py`` with the following content inside the example folder:

.. literalinclude:: ../../../templates_and_examples/examples/workflows/airflow-components/dags/example/ExtractStudyIdOperator.py

.. hint::
   | Since the operators inherits from the ``KaapanaBaseOperator.py`` all the environment variables that we have defined earlier manually are passed now automatically to the container. Studying the ``KaapanaBaseOperator.py`` you see that you can pass e.g. also a dictionary called ``env_vars`` in order to add additional environment variables to your Docker container! 

* In order to use this operator, create a file called ``dag_example_extract_study_id.py`` with the following content inside the Dag directory:

.. literalinclude:: ../../../templates_and_examples/examples/workflows/airflow-components/dags/dag_example_extract_study_id.py

* Now you can again test the final dag by executing it via the Meta-Dashboard to some image data. If everything works fine, you will find the generated data in Minio.  

In the ``templates_and_examples`` folder you will find even more example for DAGs and Docker containers!


