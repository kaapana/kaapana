.. _processing_dev_guide:

Processing Dev-Guide
====================

Introduction
------------

Write your first own DAG
^^^^^^^^^^^^^^^^^^^^^^^^

**Aim**: Create a DAG that converts DICOMs to ``.nrrd`` files

In order to deploy now a new DAG that convert DICOMs to nrrds, create a file called ``dag_example_dcm2nrrd.py`` inside the ``dags``-folder with the following content:

.. literalinclude:: ../../../templates_and_examples/examples/processing-pipelines/example/extension/docker/files/dag_example_dcm2nrrd.py
    
That's it basically. Now we can check if the DAG is successfully added to Airflow and then we can test our workflow!

* Go to Airflow and check if your newly added DAG ``example-dcm2nrrd`` appears under DAGs (it might take up to five minutes that airflow recognizes the DAG! Alternatively you could restart the Airflow Pod in Kubernetes)
* If there is an error in the created DAG file like indexing, library imports, etc., you will see an error at the top of the Airflow page
* Go to the Meta-Dashboard 
* Filter via the name of your dataset and with ``+/-`` icons on the different charts your images to which you want to apply the algorithm 
* From the drop-down, choose the DAG you have created i.e. ``example-dcm2nrrd`` and press the start button. In the appearing pop-up window press start again and the execution of your DAG is triggered.
* In order to check if your DAG runs successfully, you can go back to Airflow and watch how the pipeline jumps from one operator to the next. If an error occurs please check out the TODO section.
* If everything was successful you can go to Minio where you will find a bucket called ``example-dcm2nrrd``. Inside this folder you will find the ``.nrrd`` files of the selected images.

.. _Deploy an own processing algorithm to the platform:

Deploy an own processing algorithm to the platform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In this chapter we will write an exemplary workflow that opens a DICOM file with Pydicom, extracts the study id, saves the study id in a json file and pushes the json file to Minio.

We introduce two different workflows to realize this goal. The first workflow will be called the "integrated workflow" and, as the name says, 
integrates the development process into the environment of a running Kaapana platform, which gives us access to the resources of running Kaapana instance, especially all data.
The second workflow is called the "local workflow" and describes how one can emulate the Kaapana environment on a local machine.

Integrated Kaapana development workflow
----------------------------------------

.. _Provide an empty base image:

Step 1: Provide an empty base image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In Kaapana every component is provided inside a docker container. To develop an algorithm within the Kaapana instance we have to provide a container, to start with. Since we 
provide our algorithm as a python implementation of a DAG (see: :ref:`Write your first own DAG`), we start with a minimal python image:

.. code-block:: docker

    FROM local-only/base-python-alpine:0.1.0
    LABEL IMAGE="python-template"
    LABEL VERSION="0.1.0"
    LABEL CI_IGNORE="True"

To utilize our base image, we have to push it to our registry. 

.. code-block:: bash

    sudo docker build -t <docker-registry><docker-repo>/example-extract-study-id:0.1.0
    sudo docker push

Since we just used a generic python image as a template for our algorithm and made it available in the Kaapana registry, we can also reuse it for any other
python based algorithm.
.. TODO evtl image korrekt taggen

.. _Create a developement DAG:

Step 2: Create a development DAG
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the next step we want to load our python base image inside the Kaapana platform and access it with the built-in code server to implement our algorithm there.
To do so, we need to create an operator that loads the image and a DAG that executes the operator.

We define the operator in a file located under ``dags/example``:

.. literalinclude:: ../../../templates_and_examples/examples/processing-pipelines/example/extension/docker/files/example/ExtractStudyIdOperator.py

The DAG can look like this:

.. literalinclude:: ../../../templates_and_examples/examples/processing-pipelines/example/extension/docker/files/dag_example_extract_study_id.py 

The DAG is just a sequence of different operators. In our example the ``LocalGetInputDataOperator`` 
loads the data we want to work with. The ``ExtractStudyIdOperator`` loads our empty base image and utilizes the Kaapana code-server as development server 
to implement our algorithm inside the active container. This is achieved by the ``dev_server="code-server"`` parameter.

.. _Start the Dag and implement the algorithm:

Step 3: Start the Dag and implement the algorithm
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now we want to trigger the DAG, so we go to the meta-dashboard, select the data we want to work with and run our DAG. 
Our DAG should now be listed in the "pending applications" tab, as shown below. To access the code server we click on the blue link icon beside the name of the DAG.

We can now implement and test our algorithm. In our example the algorithm is a python script, that extracts the study IDs from the loaded data and returns it.

.. note::
    The code server looks for the ``kaapanasrc`` directory by default. When we use it as dev-server inside the docker container it will prompt an error message, that ``kaapanasrc`` 
    does not exist. You can safely ignore this and go to ``/`` to implement the algorithm. 

.. literalinclude:: ../../../templates_and_examples/examples/processing-pipelines/example/processing-containers/extract-study-id/files/extract_study_id.py

We just store the python file in the root directory of the docker container, e.g. as ``/extract_study_id.py``.

.. _Push the algorithm to the repository:

Step 3: Push the algorithm to the repository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When we are finished with the implementation, we can push the algorithm to our registry. To do so, we create a ``files`` 
directory beside the docker file of the original container and 
put a copy of our script inside it. Then we adjust our docker file such that the container executes the script.

.. literalinclude:: ../../../templates_and_examples/examples/processing-pipelines/example/processing-containers/extract-study-id/Dockerfile

Afterwards we can build and push the finished image to our registry.

.. code-block:: bash

    sudo docker build -t <docker-registry><docker-repo>/example-extract-study-id:0.1.0
    sudo docker push

Since we finished the implementation process we also don't want the DAG to initiate a dev-server every time, we can 
delete the ``dev-serve="code-server"`` option from the initialization of the ``ExtractStudyIdOperator`` in 
``dag_example_extract_study_id.py``.

.. _Local development workflow:

Local development workflow
---------------------------

Alternatively we can also develop our algorithm on a local machine and then build and push 
the resulting docker container to our registry.

To do so we need to download the data we want to work with. To access the DICOM data for our example, go to the 
Meta-dashboard, select the data you want and trigger the ``download-selected-files`` DAG. 

Additionally, we need to emulate the Kaapana environment on the local machine. We can achieve this by setting several environment variables, which would usually 
be configured by Kaapana automatically. In our case we can just configure the environment variables in the beginning of 
our python script:

.. code-block:: python

    import os

    os.environ["WORKFLOW_DIR"] = "<your data directory>"
    os.environ["BATCH_NAME"] = "batch"
    os.environ["OPERATOR_IN_DIR"] = "initial-input"
    os.environ["OPERATOR_OUT_DIR"] = "output"

Afterwards we build and push the docker container as described in :ref:`Push the algorithm to the repository`. 
To run the algorithm in Kaapana we load it with an operator and build a DAG as described in :ref:`Create a developement DAG`.  
