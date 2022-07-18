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

All of the below examples are taken from the ``templates_and_examples`` folder of our Github repository!

Preparations for the development
--------------------------------
**Requirements:**

* Running version of the Kaapana platform and access to a terminal where the platform is running
* Installation of `Docker <https://docs.docker.com/get-docker/>`_ on your local machine
* Installation of `DCMTK <https://dicom.offis.de/dcmtk.php.en>`_ (optional: convenient way to send images to the platform)

**Upload images to the platform**

* You have two options to upload images to the platform

   * Using that Data Upload: Create a zip file of images that end with .dcm and upload the images via drag&drop on the landing page in the section "Data upload"

   * Send images with dcmtk e.g.:

::

   dcmsend -v <ip-address of server> 11112  --scan-directories --call <aetitle of images, used for filtering> --scan-pattern '*'  --recurse <data-dir-of-DICOM images>

* Go to Meta on the landing page to check if the images were successfully uploaded
* In order to create a development environment to add new DAGs to the platform go to the extension section on the landing page and install the code-server-chart. Clicking on the link you will be served with a Visual Studio Code environment in the directory of Airflow, where you will find the Kaapana plugin (``workflows/plugins``), the data during processing (``workflows/data``), the models (``workflows/models``) and the directory for the DAGs definition (``workflows/dags``). 

In order to get a general idea about how to use the platform checkout TODO. Furthermore, it might be helpful to check out the TODO in order to get an idea of the concepts of the Kaapana platform.

.. _Write your first own DAG:

Write your first own DAG
^^^^^^^^^^^^^^^^^^^^^^^^

**Aim**: Create a DAG that converts DICOMs to ``.nrrd`` files

In order to deploy now a new DAG that convert DICOMs to nrrds, create a file called ``dag_example_dcm2nrrd.py`` inside the ``dags``-folder with the following content:

.. literalinclude:: ../../templates_and_examples/examples/workflows/airflow-components/dags/dag_example_dcm2nrrd.py
    
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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In this chapter we will write an exemplary workflow that opens a DICOM file with Pydicom, extracts the study id, saves the study id in a json file and pushes the json file to Minio.

We introduce two different workflows to realize this goal. The first workflow will be called the "integrated workflow" and, as the name says, 
integrates the developement process into the environment of a running kaapana platform, which gives us access to the resources of running kaapana instance, especially all data.
The second workflow is called the "local workflow" and describes how one can emulate the kaapana environment on a local machine.

Integrated Kaapana developement workflow
----------------------------------------

.. _Provide an empty base image:

Step 1: Provide an empty base image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In Kaapana every component is provided inside a docker container. To develop an algorithm within the kaapana instance we have to provide a container, to start with. Since we 
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

Since we just used a generic python image as a template for our algorithm and made it available in the kaapana registry, we can also reuse it for any other
python based algorithm.
TODO evtl image korrekt taggen

.. _Create a developement DAG:

Step 2: Create a developement DAG
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the next step we want to load our python base image inside the kaapana platform and access it with the built in code server to implement our algorithm there.
To do so, we need to create an operator that loads the image and a DAG that executes the operator.

We define the operator in a file located under ``dags/example``:

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/extract-study-id/extension/docker/files/extract-study-id/ExtractStudyIdOperator.py

The DAG can look like this:

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/extract-study-id/extension/docker/files/dag_example_extract_study_id.py (edited) 

The DAG is just a sequence of different operaters. In our example the ``LocalGetInputDataOperator`` 
loads the data we want to work with. The ``ExtractStudyIdOperator`` loads our empty base image and utilizes the kaapana code-server as developement server 
to implement our algorithm inside the active container. This is is achieved by the ``dev_server="code-server"`` parameter.

.. _Start the Dag and implement the algorithm:

Step 3: Start the Dag and implement the algorithm
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now we want to trigger the DAG, so we go to the meta-dashboard, select the data we want to work with and run our DAG. 
Our DAG should now be listed in the "pending applications" tab, as shown below. To access the code server we click on the blue link icon beside the nam of the DAG.

We can now implement and test our algorithm. In our example the algorithm is a python script, that extracts the study IDs from the loaded data and returns it.

.. note::
    The code server looks for the ``kaapanasrc`` directory by default. When we use it as dev-server inside the docker container it will prompt an error message, that ``kaapanasrc`` 
    does not exist. You can safely ignore this and go to ``/`` to implement the algorithm. 

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/extract-study-id/proccessing-containers/files/extract_study_id.py

We just store the python file in the root direcory of the docker container, e.g. as ``/extract_study_id.py``.

.. _Push the algorithm to the repository:

Step 3: Push the algorithm to the repository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When we are finished with the implementation, we can push the algorithm to our registry. To do so, we create a ``files`` 
directory beside the docker file of the original container and 
put a copy of our script inside it. Then we adjust our dockerfile such that the container executes the script.

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/extract-study-id/proccessing-containers 

Afterwards we can build and push the finished image to our registry.

.. code-block:: bash

    sudo docker build -t <docker-registry><docker-repo>/example-extract-study-id:0.1.0
    sudo docker push

Since we finished the implementation process we also don't want the DAG to initiate a dev-server everytime, we can 
delete the ``dev-serve="code-server"`` option from the initialization of the ``ExtractStudyIdOperator`` in 
``dag_example_extract_study_id.py``.

.._Local developement workflow:

Local developement workflow
---------------------------

Alternatively we can also develop our algorithm on a local machine and then nuild and push 
the rsulting docker container to our registry.

To do so we need to download the data we want to work with. To access the DICOM data for our example, go to the 
Meta-dashboard, select the data you want and trigger the ``download-selected-files`` DAG. 

Additionally we need to emulate the kaapana environement on the local machine. We can achieve this by setting several environment variables, which usually would 
be configured by kaapana automatically. In our case we can just configure the environment variables in the beginning of 
our python script:

.. code-block:: python

    import os

    os.environ["WORKFLOW_DIR"] = "<your data directory>"
    os.environ["BATCH_NAME"] = "batch"
    os.environ["OPERATOR_IN_DIR"] = "initial-input"
    os.environ["OPERATOR_OUT_DIR"] = "output"

Afterwards we build and push the docker container as described in :ref:`Push the algorithm to the repository`. 
To run the algorithm in kaapana we load it with an operator and build a DAG as described in :ref:`Create a developement DAG`.  


.. _Deploy a Flask Application on the platform:

Deploy a Flask Application on the platform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Aim**: Deploy a hello-world flask application to the Kaapana platform

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

In case you want to push the helm chart to a registry you first need to do the following steps:

* Install two plugins on the server:

:: 

   helm plugin install https://github.com/instrumenta/helm-kubeval
   helm plugin install https://github.com/chartmuseum/helm-push

* Add the helm-repo to which you want to push the data:

::
   
   helm repo add --username <username> --password <password> <repo-name> https://dktk-jip-registry.dkfz.de/chartrepo/<repo-name>

* Push the helm chart to your repo:

::

   helm push hello-world-chart <repo-name>

* Finally, after a ``helm repo update``, you can install the ``hello-world-chart`` with:

.. code-block:: python

   helm install --version 0.1.0 hello-world-chart <repo-name>/hello-world-chart

Also here the chart can be deleted again with:

::

   helm uninstall hello-world-chart


Step 5: Provide the application as an extension
------------------------------------------------

In order for Kaapana platform to recognize the application as an extension you should first copy the files into ``/services/applications/hello-world/hello-world-chart`` and add it to the requirements file of ``kaapana-stab-extensions`` chart which manages the extensions. 

::

   cp -R templates_and_examples/examples/services/hello-world services/applications/
   cd services/extensions-manager/kaapana-extensions/kaapana-stab-extensions/docker/

Add the following lines to ``files/requirements.yaml``

:: 

  - name: hello-world-chart
    version: 0.1.0
    repository: file://../../../../../../services/applications/hello-world/hello-world-chart

Run ``helm dep up`` to update helm dependencies. You should now see ``hello-world-chart-0.1.0.tgz`` file inside the ``/charts`` folder.
Next, build and push the docker container 
::
   docker build -t <docker-registry>/<docker-repo>/kaapana-stab-extensions:0.1.0 .
   docker push <docker-registry>/<docker-repo>/kaapana-stab-extensions:0.1.0

Last step is to restart the ``kaapana-stab-extensions`` pod. You can either delete the pod manually using ``kubectl`` or you can click the button next to **Applications and workflows** in the Extensions page.

Since in the ``Chart.yaml`` definition we have added ``kaapanaapplication`` to the keywords, your application should also appear in the extension list now.

.. _Provide a workflow as an extension:

Provide a workflow as an extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Similar to the previous chapter, we will start from an example workflow inside the ``templates_and_examples/examples`` folder and add it as an extension to the Kaapana platform.

.. note::
   This part is designed to be a step by step process that you can follow for 
   deploying your own DAGs on Kaapana platform using a similar folder structure.

Step 1: Copy the files into ``workflows/`` folder
---------------------------------------------------

Inside the Kaapana directory:

::

   cp -R templates_and_examples/examples/workflows/airflow-components/dags/* workflows/airflow-components/dags/
   cp -R templates_and_examples/examples/workflows/dag-installer/example workflows/dag-installer/
   cp -R templates_and_examples/examples/workflows/processing-container/* workflows/processing-container/


Step 2: Push the processing container and DAG
------------------------------------------------

We will build the ``extract-study-id`` operator first. If not already done, you have to login to your Docker registry via ``sudo docker login <docker-registry>/<docker-repo>``

::

   cd workflows/processing-container/extract-study-id
   docker build -f Dockerfile -t <docker-registry>/<docker-repo>/example-extract-study-id:0.1.0 .`   
   sudo docker push <docker-registry>/<docker-repo>/example-extract-study-idn:0.1.0`


Next, go back to the ``airflow-components`` folder and build the DAG

::

   cd ../../airflow-components/
   docker build -t <docker-registry>/<docker-repo>/dag-example:0.1.0 -f ../dag-installer/example/Dockerfile.example
   sudo docker push <docker-registry>/<docker-repo>/dag-example:0.1.0


Step 3: Helm package
---------------------------------------------------

Similar to the application deployment, we will package a Helm chart for our workflow. First we should go to dag-installer folder via ``cd ../../workflows/dag-installer/``. 

.. hint::

  | Notice that in ``example/example-workflow/Chart.yaml`` we know have ``kaapanaworkflow`` as a keyword instead of ``kaapanaapplication``

Next we will update helm dependencies and build the chart.

::

   helm dep up
   helm package .
   helm install --set-string global.registry_url=<private-registry>  --set-string global.credentials_registry_username=<username> --set-string global.credentials_registry_password=<password> example-workflow example-workflow-0.1.0.tgz


Run ``helm ls`` and you should see ``example-workflow``


Step 4: Restart ``kaapana-stab-extensions`` pod
---------------------------------------------------

First move to the chart directory with ``cd ../../services/extensions-manager/kaapana-extensions/kaapana-stab-extensions/docker/`` and add the DAG path ``files/requirements.yaml`` file as follows

::

  - name: example-workflow
    version: 0.1.0
    repository: file://../../../../../../workflows/dag-installer/example/example-workflow


Create the tgz file via ``helm dep up`` and push the new docker container via

::

   docker build -t <docker-registry>/<docker-repo>/kaapana-stab-extensions:0.1.0 .
   docker push <docker-registry>/<docker-repo>/kaapana-stab-extensions:0.1.0

| Same with the application deployment, the last step is to restart the ``kaapana-stab-extensions`` pod. 
| You can either delete the pod manually using ``kubectl`` or you can click the button next to **Applications and workflows** in the Extensions page.

| On the platform, you can also check the logs to see which files the pod has copied. To do that, go to 
| ``System -> Kubernetes -> Pods -> kaapana-stab-extensions pod -> logs (on top right)``

| Now on the Extensions page, if you select ``Version=all`` you should be able to see the ``example-workflow``.


