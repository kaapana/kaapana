.. _service_dev_guide:

Service Dev-Guide
=================

Introduction
------------

Deploy a Flask Application on the platform
------------------------------------------

**Aim**: Deploy a hello-world flask application to the Kaapana platform

Step 1: Create and run our Flask app locally
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
As a starting point, we first develop a Flask application and run it locally.
The source code of the Hello-World Flask application can be found in the ``templates_and_examples/examples/services/hello-world/docker/files``!
In case you have never worked with Flask `this  <https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world>`_ tutorial will get you started!


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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order for Kaapana platform to recognize the application as an extension you should first copy the files into ``/services/applications/hello-world/hello-world-chart`` and add it to the requirements file of ``kaapana-stab-extensions`` chart which manages the extensions. 

::

   cp -R templates_and_examples/examples/services/hello-world services/applications/
   cd services/extensions-manager/kaapana-extensions/kaapana-stab-extensions/docker/

Add the following lines to ``files/requirements.yaml``

:: 

  - name: hello-world-chart
    version: 0.1.0
    repository: file://../../../../../../../../../services/applications/hello-world/hello-world-chart

Run ``helm dep up`` to update helm dependencies. You should now see ``hello-world-chart-0.1.0.tgz`` file inside the ``/charts`` folder.
Next, build and push the docker container 
::
   
   docker build -t <docker-registry>/<docker-repo>/kaapana-stab-extensions:0.1.0
   docker push <docker-registry>/<docker-repo>/kaapana-stab-extensions:0.1.0

Last step is to restart the ``kaapana-stab-extensions`` pod. You can either delete the pod manually using ``kubectl`` or you can click the button next to **Applications and workflows** in the Extensions page.

Since in the ``Chart.yaml`` definition we have added ``kaapanaapplication`` to the keywords, your application should also appear in the extension list now.

.. _Provide a workflow as an extension:

Provide a workflow as an extension
----------------------------------

Similar to the previous chapter, we will start from an example workflow inside the ``templates_and_examples/examples`` folder and add it as an extension to the Kaapana platform.

.. note::
   This part is designed to be a step by step process that you can follow for 
   deploying your own DAGs on Kaapana platform using a similar folder structure.

Step 1: Copy the files into ``workflows/`` folder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Inside the Kaapana directory:

::

   cp -R templates_and_examples/examples/workflows/airflow-components/dags/* workflows/airflow-components/dags/
   cp -R templates_and_examples/examples/workflows/dag-installer/example workflows/dag-installer/
   cp -R templates_and_examples/examples/workflows/processing-container/* workflows/processing-container/


Step 2: Push the processing container and DAG
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We will build the ``extract-study-id`` operator first. If not already done, you have to login to your Docker registry via ``sudo docker login <docker-registry>/<docker-repo>``

::

   cd workflows/processing-container/extract-study-id
   docker build -f Dockerfile -t <docker-registry>/<docker-repo>/example-extract-study-id:0.1.0 .`   
   sudo docker push <docker-registry>/<docker-repo>/example-extract-study-idn:0.1.0`


Next, go back to the ``airflow-components`` folder and build the DAG

::

   cd ../../../airflow-components/
   docker build -t <docker-registry>/<docker-repo>/dag-example:0.1.0 -f ../dag-installer/example/Dockerfile.example
   sudo docker push <docker-registry>/<docker-repo>/dag-example:0.1.0


Step 3: Helm package
^^^^^^^^^^^^^^^^^^^^

Similar to the application deployment, we will package a Helm chart for our workflow. First we should go to dag-installer folder via ``cd ../../../workflows/dag-installer/``. 

.. hint::

  | Notice that in ``example/example-workflow/Chart.yaml`` we know have ``kaapanaworkflow`` as a keyword instead of ``kaapanaapplication``

Next we will update helm dependencies and build the chart.

::

   helm dep up
   helm package .
   helm install --set-string global.registry_url=<private-registry>  --set-string global.credentials_registry_username=<username> --set-string global.credentials_registry_password=<password> example-workflow example-workflow-0.1.0.tgz


Run ``helm ls`` and you should see ``example-workflow``


Step 4: Restart ``kaapana-stab-extensions`` pod
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

First move to the chart directory with ``cd ../../../services/extensions-manager/kaapana-extensions/kaapana-stab-extensions/docker/`` and add the DAG path ``files/requirements.yaml`` file as follows

::

  - name: example-workflow
    version: 0.1.0
    repository: file://../../../../../../../../../workflows/dag-installer/example/example-workflow


Create the tgz file via ``helm dep up`` and push the new docker container via

::

   docker build -t <docker-registry>/<docker-repo>/kaapana-stab-extensions:0.1.0 .
   docker push <docker-registry>/<docker-repo>/kaapana-stab-extensions:0.1.0

| Same with the application deployment, the last step is to restart the ``kaapana-stab-extensions`` pod. 
| You can either delete the pod manually using ``kubectl`` or you can click the button next to **Applications and workflows** in the Extensions page.

| On the platform, you can also check the logs to see which files the pod has copied. To do that, go to 
| ``System -> Kubernetes -> Pods -> kaapana-stab-extensions pod -> logs (on top right)``

| Now on the Extensions page, if you select ``Version=all`` you should be able to see the ``example-workflow``.
