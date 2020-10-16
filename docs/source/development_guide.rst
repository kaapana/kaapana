.. _dev_guide_doc:

Development Guide
=================

This guide is intended to provide a quick and easy way to get started with developments on the platform.
 
The guide currently consists of three parts. The parts :ref:`Write your first own DAG` and :ref:`Deploy an own processing algorithm to the platform` focus on the implementation of pipelines for Airflow in order to apply processing steps to images. The part :ref:`Deploy a Flask Application on the platform` explains how to develop a flask web application and integrate it as an extension into the Kaapana technology stack.

List of the technologies used within this guide
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
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

   dcmsend -v 10.128.129.28 11112  --scan-directories --call <aetitle of images, used for filtering> --scan-pattern '*'  --recurse <data-dir-of-DICOM images>

* Go to Meta on the landing page to check if the images were successfully uploaded
* In order to create a development environment to add new DAGs to the platform go to the extension section on the landing page and install the code-server-chart. Clicking on the link you will be served with a Visual Studio Code environment in the directory of Airflow, where you will finde the Kaapana plugin (``workflows/plugins``), the data during processing (``workflows/data``), the models (``workflows/models``) and the directory for the DAGs definition (``workflows/dags``). 

In order to get a general idea about how to use the platform checkout TODO. Furthermore, it might be helpful to check out the TODO in order to get an idea of the concepts of the Kaapana platform.

.. _Write your first own DAG:

Write your first own DAG
^^^^^^^^^^^^^^^^^^^^^^^^

**Aim**: Create a DAG that converts DICOMs to ``.nrrd`` files

In order to deploy now a new DAG that convert DICOMs to nrrds, create a file called ``dag_example_dcm2nrrd.py`` inside the ``dags``-folder with the following content:

.. literalinclude:: ../../templates_and_examples/examples/workflows/airflow-components/dags/dag_example_dcm2nrrd.py
    
That's it basically. Now we can check if the DAG is successfully added to Airflow and then we can test our workflow!

* Go to Airflow via the landing page and check if your newly added DAG ``example-dcm2nrrd`` appears under DAGs (it might take up to five minutes that airflow recognizes the DAG! Alternatively you could restart the Airflow Pod in Kubernetes)
* If there is an error in the created DAG file like indexing, library imports, etc, you will see an error at the top of the Airflow page
* Go to the Meta-Dashboard via the landing page 
* Filter via the name of your dataset and with ``+/-`` icons on the different charts your images to which you want to apply the algorithm 
* From the drop-down, choose the DAG you have created i.e. ``example-dcm2nrrd``, and in the second dropdown choose ``batch file processing``, like this, one single instead of multiple processing pipelines are triggered for all the images selected.
* In order to check if your DAG runs successfully, you can go back to Airflow and watch how the pipeline jumps from one operator to the next. If an error occurs please check out the TODO section.
* If everything was successful you can go to Minio via the landing page where you will find a bucket called ``example-dcm2nrrd``. Inside this folder you will find the ``.nrrd`` files of the selected images.

.. _Deploy an own processing algorithm to the platform:

Deploy an own processing algorithm to the platform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Aim:** We will write a workflow that opens a DICOM file with Pydicom, extracts the study id, saves the study id in a json file and pushes the json file to Minio.

Step 1: Check if our scripts works locally
------------------------------------------
First of all, it is important that your script works. For this, we will simulate the folder structure that we expect on the platform and apply our algorithm locally to the files. In order to simulate the folder structure. Please go back to the Meta-Dashboard, select the files you want to develop with and trigger the DAG ``download-selected-files`` with option zip files ``False``. This will download the selected images to a folder in Minio. Please go to Minio, download the folder called ``batch`` and save the extracted content to a folder called ``data``. Now the ``data`` folder corresponds to the ``data`` folder that you have seen in the workflows folder.

.. hint::

  | In case your algorithm works with ``.nrrd`` files you could simply download the batch folder that we generated in the example-dcm2nrrd folder

* Now we create the following python script ``extract_study_id.px``. Make sure that we have Pydicom installed:

.. literalinclude:: ../../templates_and_examples/examples/workflows/docker-container/extract-study-id/files/extract_study_id.py

.. hint::

  | When creating a new algorithm you can always take our templates (``templates_and_examples/templates/docker-container``) as a starting point and simply add your code snippet in between for the processing.

In order to test the script we uncomment the os.environ sections and adapt the ``WORKFLOW_DIR`` to the ``data`` location on our local file system. Then we execute the script. On the platform all the environment variables will be set automatically. If the algorithm runs without errors, the most difficult part is already done, we have a running workflow!

Step 2: Check if our scripts runs inside a Docker container
-----------------------------------------------------------

The next step is to put the algorithm into a Docker container and test if everything works as expected. For this we will put the ``extract_study_id.py`` in a folder called ``files``, comment again the os.environ section and create the following file called ``Dockerfile`` next to the files directory:

.. literalinclude:: ../../templates_and_examples/examples/workflows/docker-container/extract-study-id/Dockerfile

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
------------------------------------------------------------------------------------------

Now, we will embed the created Docker container into an operator that will be part of an Airflow DAG.

* Go again to the code-server ``/code``
* Create a folder called ``example`` inside the ``dags`` directory
* Create a file called ``ExtractStudyIdOperator.py`` with the following content inside the example folder:

.. literalinclude:: ../../templates_and_examples/examples/workflows/airflow-components/dags/example/ExtractStudyIdOperator.py

.. hint::
   | Since the operators inherits from the ``KaapanaBaseOperator.py`` all the environment variables that we have defined earlier manually are passed now automatically to the container. Studying the ``KaapanaBaseOperator.py`` you see that you can pass e.g. also a dictionary called ``env_vars`` in order to add additional environment variables to your Docker container! 

* In order to use this operator, create a file called ``dag_example_extract_study_id.py`` with the following content inside the Dag directory:

.. literalinclude:: ../../templates_and_examples/examples/workflows/airflow-components/dags/dag_example_extract_study_id.py

* Now you can again test the final dag by executing it via the Meta-Dashboard to some image data. If everything works fine, you will find the generated data in Minio.  

In the ``templates_and_examples`` folder you will find even more example for DAGs and Docker containers!


.. _Deploy a Flask Application on the platform:

Deploy a Flask Application on the platform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Aim**: Deploy a hello-world flask application to the Kaapana platform

Step 1: Create and run our Flask app locally
--------------------------------------------
As a starting point, we first develop a Flask application and run in locally. The source code of the Hello-World Flask application can be found in the ``templates_and_examples/examples/services/hello-world``! In case you have never worked with Flask `this  <https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world>`_ tutorial will get you started!


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


Step 4: Write a helm chart and provide it as an extensions 
----------------------------------------------------------

For only local testing you can go to the ``hello-world`` directory and build the helm chart locally with:

::

   helm package hello-world-chart

This will generate a file called ``hello-world-chart-0.1.0.tgz``, which can be install on the platform with:

::
   
   helm install hello-world-chart hello-world-chart-0.1.0.tgz

Now, you should have the same result as before, when you created the deployment with ``kubectl``. With ``helm ls`` you can view all helm releases that are currently running.

In order to remove the chart execute:

::

   helm delete hello-world-chart

In case you want to push the helm chart to a registry you first need to do the following steps:

* Install two plugins on the server (if you are on CentOS you might need to install git first with ``sudo yum install git``):

:: 

   helm plugin install https://github.com/instrumenta/helm-kubeval
   helm plugin install https://github.com/chartmuseum/helm-push

* Add the helm-repo to which you want to push the data:

::
   
   helm repo add --username <username> --password <password> <repo-name> https://dktk-jip-registry.dkfz.de/chartrepo/<repo-name>

* Push the helm chart to your repo

   helm push hello-world-chart <repo-name>

* Finally, after a ``helm repo update``, you can install the ``hello-world-chart`` with:

.. code-block:: python

   helm install --version 0.1.0 hello-world-chart <repo-name>/hello-world-chart

Also here the chart can be deleted again with:

::

   helm delete hello-world-chart

Since in the ``Chart.yaml`` definition we have added ``kaapanextension`` to the keywords, your application should also appear in the extension list. If it does not you might need to update the extension list via:

::
   
   ./install_platform.sh --update-extensions


