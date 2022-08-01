.. _service_dev_guide:

Service Dev-Guide
=================

Introduction
------------

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

.. literalinclude:: ../../../templates_and_examples/examples/processing-pipelines/threshold-segmentation/processing-containers/otsus-method/files/otsus_method.py

In the :code:`otsus-method` directory create a :code:`Dockerfile` with the content:

.. literalinclude:: ../../../templates_and_examples/examples/processing-pipelines/threshold-segmentation/processing-containers/otsus-method/Dockerfile

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

.. literalinclude:: ../../../templates_and_examples/examples/processing-pipelines/threshold-segmentation/extension/docker/files/otsus-method/OtsusMethodOperator.py

Create a python file :code:`dag_example_otsus_method.py` for the DAG in the folder :code:`extension/docker/files/`

.. literalinclude:: ../../../templates_and_examples/examples/processing-pipelines/threshold-segmentation/extension/docker/files/dag_example_otsus_method.py
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

.. literalinclude:: ../../../templates_and_examples/examples/processing-pipelines/threshold-segmentation/extension/docker/Dockerfile

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

.. literalinclude:: ../../../templates_and_examples/examples/processing-pipelines/threshold-segmentation/extension/threshold-segmentation-workflow/Chart.yaml

Create a file :code:`requirements.yaml`

.. literalinclude:: ../../../templates_and_examples/examples/processing-pipelines/threshold-segmentation/extension/threshold-segmentation-workflow/requirements.yaml

.. important:: 
    The field :code:`repository` must be the relative path from the file :code:`requirements.yaml` to the directory that contains the 
    :code:`Chart.yaml` file for the dag-installer chart. This file is located in the subdirectory :code:`services/utils/dag-installer/dag-installer-chart/`
    of the kaapana repository.

Create a file :code:`values.yaml`

.. literalinclude:: ../../../templates_and_examples/examples/processing-pipelines/threshold-segmentation/extension/threshold-segmentation-workflow/values.yaml

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