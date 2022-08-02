.. _service_dev_guide:

=================
Service Dev-Guide
=================

Introduction
------------

In the service dev-guide we demonstrate how one can integrate functionalities into the Kaapana platform, that do not fit into the
structure of processing pipelines. For this purpose we show how we can host a general flask web application within Kaapana.

.. _Deploy a Flask Application on the platform:

Deploy a Flask Application on the platform
------------------------------------------

**Aim**: In this chapter we deploy a Flask application within the Kaapana platform. 

Step 1: Create and run our Flask app locally
********************************************
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
************************************************************

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
****************************************

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
**************************

For only local testing you can go to the ``hello-world`` directory and build the helm chart locally with:

::

   helm package hello-world-chart

This will generate a file called ``hello-world-chart-0.1.0.tgz``, which can be installed on the platform with:

::
   
   helm install hello-world-chart hello-world-chart-0.1.0.tgz

Alternatively, you can also set your own private registry for helm Install

::

   helm install --set-string global.registry_url=<private-registry> --set-string global.credentials_registry_username=<username> --set-string global.credentials_registry_password=<password>  hello-world-chart hello-world-chart-0.1.0.tgz


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
***********************************************
You can also add the Flask application as an extension to the Kaapana platform. To do so follow the steps described in
:ref:`Add Extension Manually` or :ref:`Add to Extention Collection`.