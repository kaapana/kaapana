.. _dev_guide_doc:

Development guide
=================

This guide is intended to provide a quick and easy way to get started with developments on the platform.
 
The guide currently consists of four parts. The parts :ref:`Write your first own DAG` and :ref:`Deploy an own processing algorithm to the platform` focus on the implementation of pipelines for Airflow in order to apply processing steps to images. The part :ref:`Deploy a Flask Application on the platform` explains how to develop a flask web application and integrate it as an extension into the Kaapana technology stack. The last section :ref:`Provide a workflow as an extension` gives step by step instructions for how to deploy your own DAG as an extension to the platform.


Getting started
^^^^^^^^^^^^^^^

List of the technologies used within this guide
-----------------------------------------------
These tutorials/technologies are good references, when starting with the Kaapana deployment:

* `Docker <https://docs.docker.com/get-docker/>`_: Necessary when you want to build container on your local machine
* `Airflow <https://airflow.apache.org/docs/stable/>`_: Our pipeline tool for processing algorithms
* `Kubernetes <https://kubernetes.io/docs/tutorials/kubernetes-basics/>`_: (Advanced) On your local machine - necessary when you want to talk to the Kubernetes cluster from your local machine
* `Helm <https://helm.sh/docs/intro/quickstart/>`_: (super advanced) - our package manager for Kubernetes.  Necessary when you want to build helm packages on your local machine

All of the examples below are taken from the ``templates_and_examples`` folder of our Github repository!

Preparations for the development
--------------------------------
**Requirements:**

* Running version of the Kaapana platform and access to a terminal where the platform is running
* Installation of `Docker <https://docs.docker.com/get-docker/>`_ on your local machine
* Installation of `DCMTK <https://dicom.offis.de/dcmtk.php.en>`_ (optional: convenient way to send images to the platform)

**Upload images to the platform**

* You have two options to upload images to the platform

   * Using that Data Upload: Create a zip file of images that end with ``.dcm`` and upload the images via drag&drop on the landing page in the section "Data upload"

   * Send images with dcmtk e.g.:

::

   dcmsend -v <ip-address of server> 11112 --scan-directories --call <aetitle of images, used for filtering> --scan-pattern '*' --recurse <data-dir-of-DICOM images>

* Go to Meta on the landing page to check if the images were successfully uploaded
* In order to create a development environment to add new DAGs to the platform go to the extension section on the landing page and install the code-server-chart. Clicking on the link you will be served with a Visual Studio Code environment in the directory of Airflow, where you will find the Kaapana plugin (``workflows/plugins``), the data during processing (``workflows/data``), the models (``workflows/models``) and the directory for the DAGs definition (``workflows/dags``). 

In order to get a general idea about how to use the platform checkout :ref:`what_is_kaapana` and https://www.kaapana.ai. Furthermore, it might be helpful to check out the :ref:`user_guide`, in order to get an idea of the concepts of the Kaapana platform.

.. _Write your first own DAG:

Write your first own DAG
^^^^^^^^^^^^^^^^^^^^^^^^

**Aim**: Create a DAG that converts DICOMs to ``.nrrd`` files

In order to deploy now a new DAG that convert DICOMs to nrrds, create a file called ``dag_example_dcm2nrrd.py`` inside the ``dags``-folder with the following content:

.. literalinclude:: ../../templates_and_examples/examples/processing-pipelines/example/extension/docker/files/dag_example_dcm2nrrd.py
    
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

.. literalinclude:: ../../templates_and_examples/examples/processing-pipelines/example/extension/docker/files/example/ExtractStudyIdOperator.py

The DAG can look like this:

.. literalinclude:: ../../templates_and_examples/examples/processing-pipelines/example/extension/docker/files/dag_example_extract_study_id.py 

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

.. literalinclude:: ../../templates_and_examples/examples/processing-pipelines/example/processing-containers/extract-study-id/files/extract_study_id.py

We just store the python file in the root directory of the docker container, e.g. as ``/extract_study_id.py``.

.. _Push the algorithm to the repository:

Step 3: Push the algorithm to the repository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When we are finished with the implementation, we can push the algorithm to our registry. To do so, we create a ``files`` 
directory beside the docker file of the original container and 
put a copy of our script inside it. Then we adjust our docker file such that the container executes the script.

.. literalinclude:: ../../templates_and_examples/examples/processing-pipelines/example/processing-containers/extract-study-id/Dockerfile

Afterwards we can build and push the finished image to our registry.

.. code-block:: bash

    sudo docker build -t <docker-registry><docker-repo>/example-extract-study-id:0.1.0
    sudo docker push

Since we finished the implementation process we also don't want the DAG to initiate a dev-server every time, we can 
delete the ``dev-serve="code-server"`` option from the initialization of the ``ExtractStudyIdOperator`` in 
``dag_example_extract_study_id.py``.

_Local development workflow:

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


.. _Provide a workflow as an extension:

Provide a workflow as an extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Aim:** We will write a workflow that applies Otsu's method to create a segmentation of DICOM data.
We want to provide this workflow as an extension to the Kaapana platform.

**Requirements:** You need the image `local-image/dag-installer:0.1.0` available in order to build the image for the DAG.

Step 1: Build an image for the processing algorithm
----------------------------------------------------

First you need to create a directory for the processing algorithm. To remain consistent with the structure of Kaapana 
we recommend create the new folder in the location 
``kaapana/data-processing/processing-piplines/``, but in theory it can be located anywhere.
::

    mkdir -p threshold-segmentation/processing-containers/otsus-method/files/

In the :code:`files` directory create a file called `otsus_method.py` that contains the segmentation algorithm based on Otsu's method:

.. literalinclude:: ../../templates_and_examples/examples/processing-pipelines/threshold-segmentation/processing-containers/otsus-method/files/otsus_method.py

In the :code:`otsus-method` directory create a :code:`Dockerfile` with the content:

.. literalinclude:: ../../templates_and_examples/examples/processing-pipelines/threshold-segmentation/processing-containers/otsus-method/Dockerfile

Starting this container will execute the segmentation algorithm.

To tag the image and push it to the registry, run the following commands inside the :code:`otsus-method` directory.

::

    docker build -t <docker-registry>/<docker-repo>/threshold-segmentation:0.1.0 .
    docker push <docker-registry>/<docker-repo>/threshold-segmentation:0.1.0

.. hint::
     If not already done, you have to log into your Docker registry with :code:`sudo docker login <docker-registry>/<docker-repo>`
     , before you build the container.

Step 2: Create an image for the DAG 
-----------------------------------

Create the folder for the DAG image. Inside the :code:`threshold-segmentation` directory run:

::

    mkdir -p extension/docker/files/otsus-method

Inside the folder :code:`extension/docker/files/otsus-method` create the :code:`OtsusMethodOperator.py` file

.. literalinclude:: ../../templates_and_examples/examples/processing-pipelines/threshold-segmentation/extension/docker/files/otsus-method/OtsusMethodOperator.py

Create a python file :code:`dag_example_otsus_method.py` for the DAG in the folder :code:`extension/docker/files/`

.. literalinclude:: ../../templates_and_examples/examples/processing-pipelines/threshold-segmentation/extension/docker/files/dag_example_otsus_method.py
.. hint :: 
    The DAG will perform the following steps:
        - Get the dicom files (LocalGetInputDataOperator), 
        - convert the dicom files to .nrrd files  (DcmConverterOperator), 
        - apply the segmentation (OtsusMethodOperator),
        - create a dicom segmentation from the .nrrd segmentation (Itk2DcmSegOperator ), 
        - send the data back to the PACS (DcmSendOperator),
        - clean the workflow dir (LocalWorkflowCleanerOperator).

    **Note:** If you want to use this DAG as a template for your own segmentation algorithm note that 
    :code:`Itk2DcmSegOperator` requires the arguments :code:`segmentation_operator` and
    :code:`single_label_seg_info`.

In :code:`extension/docker/` create the :code:`Dockerfile` for the DAG

.. literalinclude:: ../../templates_and_examples/examples/processing-pipelines/threshold-segmentation/extension/docker/Dockerfile

.. hint :: 
    The base image :code:`local-only/dag-installer:0.1.0` scans all .py files in :code:`tmp` for images and pulls them via the Helm API.
    It also copies files into desired locations.

Tag the image and push it to the registry. Next to the :code:`Dockerfile` in :code:`extension/docker/` run 

::

    docker build -t <docker-registry>/<docker-repo>/dag-example-otsus-method:kp_0.1.3__0.1.0 .
    docker push <docker-registry>/<docker-repo>/dag-example-otsus-method:kp_0.1.3__0.1.0

.. important :: 
    Setting the correct version tag is important, because the platform pulls the DAG with a specific version tag.
    This tag is build as follows: :code:`<platform-abbr>_<platform-version>__<dag-version>`.
    The :code:`platform-abbr` for the kaapana-platform is ``kp`` and for the starter-platform ``sp``.
    The :code:`platform-version` can be found at the bottom of the user interface.
    The :code:`dag-version` is specified in the :code:`Dockerfile` of the DAG.


Step 3: Create the helm chart
-----------------------------

Create a folder for the chart. Inside :code:`threshold-segmentation/extension/` run 

:: 

    mkdir -p threshold-segmentation-workflow
    cd threshold-segmentation-workflow

Create a file :code:`Chart.yaml`

.. literalinclude:: ../../templates_and_examples/examples/processing-pipelines/threshold-segmentation/extension/threshold-segmentation-workflow/Chart.yaml

Create a file :code:`requirements.yaml`

.. literalinclude:: ../../templates_and_examples/examples/processing-pipelines/threshold-segmentation/extension/threshold-segmentation-workflow/requirements.yaml

.. important:: 
    The field :code:`repository` must be the relative path from the file :code:`requirements.yaml` to the directory that contains the 
    :code:`Chart.yaml` file for the dag-installer chart. This file is located in the subdirectory :code:`services/utils/dag-installer/dag-installer-chart/`
    of the kaapana repository.

Create a file :code:`values.yaml`

.. literalinclude:: ../../templates_and_examples/examples/processing-pipelines/threshold-segmentation/extension/threshold-segmentation-workflow/values.yaml

.. hint:: 
    These three files define the helm chart that will be installed on the platform in order to provide the algorithm as a workflow.

Update helm dependencies and package the chart.

::

    helm dep up 
    helm package .

This will create the file :code:`example-threshold-segmentation-workflow-0.1.0.tgz`

.. _Add Extension Manually:

Step 4.1: Add the extension manually to the platform
-----------------------------------------------------

.. warning:: 
    This approach requires root permissions on the host server of the platform.

The easiest way to get the extension into the platform is by copying the packaged helm chart to the right location.
To do so you need access to the host machine, of the platform.
Copy the file :code:`example-threshold-segmentation-workflow-0.1.0.tgz` to the :code:`extensions/` subdirectory
of the :code:`FAST_DATA_DIR` directory, which is :code:`/home/kaapana/` by default. 

.. hint::
    The :code:`FAST_DATA_DIR` can be configured by editing the :code:`install_platform.sh`
    script before the installation of the platform.

.. warning:: 
    This approach has the disadvantage that the extension only exists in the platform that is deployed on this host machine.
    If you want to provide your algorithm on another platform instance, you have to repeat this step again.
    Step 4.2 shows a persistent approach, where your algorithm is available for each platform that is installed from your private registry.

.. _Add to Extention Collection:

Step 4.2: (Persistent alternative) Update the :code:`kaapana-extension-collection` chart
----------------------------------------------------------------------------------------

The Kaapana repository contains a special **collection** chart that depends on a list of other charts required for Kaapana.
You will add the chart of our new DAG to this list and update the dependencies to add the new extension in a persistent way.

First adjust the file :code:`collections/kaapana-collection/requirements.yaml` in your Kaapana repository.

::

    - name: example-threshold-segmentation-workflow
      version: 0.1.0
      repository: file://../../data-processing/processing-pipelines/threshold-segmentation/extension/threshold-segmentation-workflow/

.. hint:: 
    The repository field must point from the :code:`kaapana-extension-collection` chart to the directory of the chart for the DAG.

Now update the dependencies, afterwards build and push the image.
::

    helm dep up 
    docker build -t <docker-registry>/<docker-repo>/kaapana-extension-collection:kp_0.1.3__0.1.0
    docker push <docker-registry>/<docker-repo>/kaapana-extension-collection:kp_0.1.3__0.1.0

Finally restart the :code:`kaapana-extension-collection` pod. You can do this in the Kaapana gui by clicking on the cloud button next to **Applications and workflows** in the Extension page.

You can also manually delete the pod on your host machine.
First search for the name of the pod.

::

    kubectl get pods -n default

The name of the pod you need to delete begins with :code:`copy-kube-helm-collections`

::
     
    kubectl delete pod <pod-name>

This will automatically download a new version of the chart and start a new pod.



.. _Deploy a Flask Application on the platform:

Deploy a Flask Application on the platform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Aim**: In this chapter we deploy a Flask application within the Kaapana platform. 

Step 1: Create and run our Flask app locally
--------------------------------------------
As a starting point, we first develop a Flask application and run it locally. The source code of the Hello-World Flask application can be found in the ``templates_and_examples/examples/services/hello-world/docker/files``! In case you have never worked with Flask `this  <https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world>`_ tutorial will get you started!


First of all install the requirements.

::

   pip install -r requirements.txt

Now you can try to run the Flask application locally:

::

    flask run

When you go to http://localhost:5000 you should see a hello message!

Since ``flask run`` is only for development, we use Gunicorn to run in production. Gunicorn is started via the ``boot.sh`` bash script. To try it please run:

::

    SCRIPT_NAME=/hello-world gunicorn -b :5000 -e SECRET_KEY='test' -e HELLO_WORLD_USER='klaus' -e APPLICATION_ROOT='/hello-world' run:app

Now the application can be accessed via ``http://localhost:5000/hello-world``. As you can see we adapted the application to run on the prefix path ``/hello-world``. A requirement for any application running on our platform is that it runs within its own subpath, otherwise, it is only possible to serve it via http on a specific port.


Step 2: Create a Docker container with the Flask application
------------------------------------------------------------

First of all we build the docker container with:

::

   sudo docker build -t <docker-registry><docker-repo>/hello-world:0.1.0 .

.. hint::

  | Depending on your docker registry ``docker-repo`` might be not defined: ``docker-repo=''`` or the name of the docker repository!


Then check locally if the docker container works as expected:

::

   sudo docker run -p 5000:5000 -e SECRET_KEY='some-secret-key' -e HELLO_WORLD_USER='Kaapana' -e APPLICATION_ROOT='/hello-world' <docker-registry><docker-repo>/hello-world:0.1.0

Again you should be able to access the application via ``http://localhost:5000/hello-world``

Now, we need to push the docker file to the docker registry. If not already done, log in to the registry with:


If not already done, log in to the docker registry:

::

   sudo docker login <docker-registry>

and push the docker image with:
::

   sudo docker push <docker-registry><docker-repo>/hello-world:0.1.0


Step 3: Write the Kubernetes deployments 
----------------------------------------

Since the Kaapana platform runs in Kubernetes, we will create a Kubernetes deployment, service and ingress in order to get the application running inside the platform. The following steps will show how to to that:

* Replace inside the ``hello-world-chart/templates/deployment.yaml`` file the ``<docker-registry><docker-repo>`` with your docker registry.
* Copy the folder ``hello-word-chart`` to the instance where the platform is running
* Log in to the server and go to the templates directory.

Now you should be able to deploy the platform. Go to the server to the directory of the ``hello-world-chart`` folder and execute:

::

   kubectl apply -f hello-world-chart/templates/

If everything works well the docker container is started inside the Kubernetes cluster. When going to ``/hello-world`` on your platform, you should see the hello kaapana page again. Furthermore you should also be able to see the application running on the port 5000. This is because we specified a NodePort in the ``service.yaml`` file.

If the pod started successfully you can also execute:

::

 kubectl get pods -A

Then you should see your pod starting or running!

In order to remove the deployment again execute:

::

   kubectl delete -f hello-world-chart/templates/


Step 4: Write a helm chart
----------------------------------------------------------

For only local testing you can go to the ``hello-world`` directory and build the helm chart locally with:

::

   helm package hello-world-chart

This will generate a file called ``hello-world-chart-0.1.0.tgz``, which can be installed on the platform with:

::
   
   helm install hello-world-chart hello-world-chart-0.1.0.tgz

Alternatively, you can also set your own private registry for helm Install

::

   helm install --set-string global.registry_url=<private-registry>  --set-string global.credentials_registry_username=<username> --set-string global.credentials_registry_password=<password>  hello-world-chart hello-world-chart-0.1.0.tgz


Either way, you should have the same result as before when you created the deployment with ``kubectl``. With ``helm ls`` you can view all helm releases that are currently running.

In order to remove the chart execute:

::

   helm uninstall hello-world-chart --no-hooks

* To push the helm chart to a repository you can use the open container interface (oci):

::

   helm push hello-world-chart-0.1.0.tgz oci://<registry><repository>

* You can install a helm chart from a repository py pulling the image and installing it to your cluster afterwards:

.. code-block:: bash

   helm pull oci://<registry><repository>/hello-world-chart --version 0.1.0
   helm install hello-world-chart hello-world-chart-0.1.0.tgz

Also here the chart can be deleted again with:

::

   helm uninstall hello-world-chart


Step 5: Provide the application as an extension
------------------------------------------------
You can also add the Flask application as an extension to the Kaapana platform. To do so follow the steps described in
:ref:`Add Extension Manually` or :ref:`Add to Extention Collection`.