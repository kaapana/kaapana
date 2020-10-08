.. _dev_guide_doc:

Development Guide
=================

This development manual is intended to provide a quick and easy way to get started with the development of `Joint Imaging Platform <https://jip.dktk.dkfz.de/jiphomepage/>`_

.. _Joint Imaging Platform (JIP): https://jip.dktk.dkfz.de/jiphomepage/

The session is mainly divided into two parts. In part 1, you will create a DAG, and create a pipeline using airflow to trigger your algorithm and monitor the results in JIP Minio.
In part 2, you will develop a flask web application and deploy it in local, docker, Kubernetes, and helm platforms.

A Quick Walkthrough with the Technologies Used
----------------------------------------------
These tutorials/technologies will be a good starting point before starting with the JIP development guide.

1. `Development guide for DAGs <https://jip.dktk.dkfz.de/jiphomepage/42fef1/dev_guide.html>`_:  Our guide to deploying a DAG on the platform, will be extended with the contents from this tutorial.
2. `Docker registry <https://dktk-jip-registry.dkfz.de/>`_: Our docker registry that holds all the Docker Container

3. `Docker Installation <https://docs.docker.com/get-docker/>`_: Necessary when you want to build container on your local machine

4. `Airflow <https://airflow.apache.org/docs/stable/>`_: Our pipeline tool for processing algorithms
5. `Kubernetes <https://kubernetes.io/docs/tutorials/kubernetes-basics/>`_: (Advanced) On your local machine - necessary when you want to talk to the Kubernetes cluster from your local machine
6. `Helm <https://helm.sh/docs/intro/quickstart/>`_: (super advanced) - our package manager for Kubernetes
7. `Helm installation  <https://helm.sh/docs/using_helm/#installing-helm>`_: (Super advanced)- Necessary when you want to build helm packages on your local machine
8. `Flask-Mega- Tutorial  <https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world>`_: Tutorial for Flask application used partly in the example
9. `Download link   <https://jip.dktk.dkfz.de/jiphomepage/42fef1/hello-world.zip>`_: for flask example

Part - 1 Create a DAG that converts DICOMS to nrrd
--------------------------------------------------

Before proceeding to the next steps, ensure that the following assumptions are correct.

**Assumptions:**


 * You have a working open stack instance `Set up OpenStack Instance  <https://phabricator.mitk.org/w/dktk-jip/dkfz-openstack/>`_

 * Your JIP is configured and  can see the JIP welcome homepage with your floating IP, for example in  https://xx.xx.xx.xx

*If the above assumptions are met, please proceed to the below steps*

 * Go to /code/ (for example, if your JIP is running on https://xx.xx.xx.xx, then to view the online code repo, the URL should be https://xx.xx.xx.xx/code/)

 * Now an online Visual Studio Code editor should be opened

 * Create a file called dag_dcm2nrrd.py under the workflows/dags folder 

**Creating the python DAG script**

::

    from airflow.utils.log.logging_mixin import LoggingMixin
    from airflow.utils.dates import days_ago
    from datetime import timedelta
    from airflow.models import DAG
    from dcipher.operators.LocalPushFiles2MinioOperator import LocalPushFiles2MinioOperator
    from dcipher.operators.DcmConverterOperator import DcmConverterOperator
    
    log = LoggingMixin().log
    
    args = {
    'owner': 'airflow',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
    }
    
    dag = DAG(
    dag_id='dcm2nrrd',
    default_args=args,
    concurrency=20,
    max_active_runs=10,
    schedule_interval=None)
    
    
    convert = DcmConverterOperator(dag, output_format='nrrd')
    
    push_to_minio = LocalPushFiles2MinioOperator(dag=dag, push_operators=[convert], file_white_tuples=('.nrrd'))
    
    convert >> push_to_minio
    
**To Trigger The Workflow**

* Go to Airflow (either via jip home page - > flow -> airflow or <INSTANCE_IP> /flow and check if your newly added DAG dag_dcm2nrrd’ shown under DAG column

* If there is an error in the created DAG file like indexing, library imports, etc, you could see that error at the top of  the Airflow page

* Go to Meta(either via jip home page or via <INSTANCE_IP>/meta) 

* From the first drop-down, choose the DAG you have created ie dcm2nrrd,  from next drop down choose the number of files to be processed, in this case, its ‘single file processing’.

* There are many filtration logics provided, you could filter files in the ‘Modality Donut’ section by clicking the appropriate field value you want and in the section ‘Dataset’, you could filter values based on clicking the +/- icon and trigger your workflow, click ‘Yes’ to the pop-up message.

* Go to  Minio (<INSTANCE_IP>/minio) :code:`username`: *jipadmin*, :code:`password`: *DKjipTK2019*) and download the folder “batch”-folder; Take a look at the folder structure

Part - 2 Deploy a Flask Application on the platform
---------------------------------------------------

The goal of this session is to deploy a hello-world application (`Download link   <https://jip.dktk.dkfz.de/jiphomepage/42fef1/hello-world.zip>`_) in Local, Docker, Kubernetes, and Helm platform.

**Local development**


The following assumption should meet before proceeding to the next part of this tutorial.

**Assumptions**

 * Docker is running on your local machine.
 * You have a working open stack instance.
 * Your JIP is configured and  can see the JIP welcome homepage with your floating IP,          for example in  https://xx.xx.xx.xx
 * The following required libraries are installed in local machine, if not, install them using the below commands.

Please install the required libraries using requirement.txt which can be found under :code:`project folder->docker -> files-> requirements.txt`

::

    pip install -r requirements.txt

To run the application locally either run via flask command or gunicorn command can be used. Both are given below.

**Run Flask application locally:**

::

    flask run

**Run with gunicorn on subpath:**

In this method, we are deploying the application via gunicorn (Gunicorn 'Green Unicorn' is a Python WSGI HTTP Server for UNIX) by triggering a shell script.
The boot.sh script is given below and it can be found under 
:code:`Docker -> Files -> boot.sh`

::

    SCRIPT_NAME=/hello-world gunicorn -b :5000 -e SECRET_KEY='test' -e HELLO_WORLD_USER='klaus' -e APPLICATION_ROOT='/hello-world' run:app

Once you trigger the script, the application can be accessed via http://0.0.0.0:5000/hello-world or http://localhost:5000/hello-world


**Deploying the application in Docker**

The goal is to deploy the hello-world application in docker and push it to the Docker registry.
Now, open the Dockerfile from the directory :code:`docker -> Dockerfile` and export the environment variables as given below in the terminal.


.. code-block:: 

    export DOCKER_REGISTRY="dktk-jip-registry.dkfz.de"
    export DOCKER_REPO="tutorial"
    export IMAGE="hello-world"
    export VERSION="1.0-dkfz"

Now, run the below command to build the docker image on the root directory of Dockerfile.

.. code-block:: 

  sudo docker build -t $DOCKER_REGISTRY/$DOCKER_REPO/$IMAGE:$VERSION .

**To deploy the docker image Run on your local machine**

.. code-block:: 

   sudo docker run -p 5000:5000 -e SECRET_KEY='jip' -e HELLO_WORLD_USER='Klaus' -e APPLICATION_ROOT='/hello-world' $DOCKER_REGISTRY/$DOCKER_REPO/$IMAGE:$VERSION



Check the http://localhost:5000/hello-world/ or http://0.0.0.0:5000/hello-world/ to ensure that the docker container is up and running

Maybe mention docker-compose to test more complex systems

**Push docker to registry**

To push the docker image to the Docker registry, you may need to log in using the below command

.. code-block::

   sudo docker login dktk-jip-registry.dkfz.de

.. code-block::

   sudo docker push $DOCKER_REGISTRY/$DOCKER_REPO/$IMAGE:$VERSION

**Writing the Kubernetes files for deployment**

The objective of this session is, managing the docker deployment using Kubernetes.


**Assumptions are:**

 * You have a cluster where the docker and Kubernetes are configured.
 * You have copied your hello-world application to the cluster

Copy the below Kubernetes config file to your project location, it can be found in open stack instance if you have run platform_installer.sh script earlier during jip configuration.

.. code-block:: python

   ~/.kube/config

The following commands need to be executed to support the helm deployment.


.. code-block:: python

   helm plugin install https://github.com/instrumenta/helm-kubeval

.. code-block:: python

   helm plugin install https://github.com/chartmuseum/helm-push


Now go to the templates directory inside the hello-world folder and Run the below command where your deployment.yaml and service.yaml is placed


.. code-block:: python

   kubectl apply -f .


Go to Platform and Kubernetes in JIP to check if everything is running (application should run on <INSTANCE_IP>/hello-world)

 * Remove deployment:

.. code-block:: python

   kubectl delete -f .


**Writing the helm deployment**

 * Adding the tutorial repo to JIP repository
 * Go to the hello-world root directory and run the below command.

.. code-block:: python

   helm repo add --username jip-ci-dcipher --password <password> tutorial https://dktk-jip-registry.dkfz.de/chartrepo/tutorial

Pushing the helm chart form the helm_charts directory

.. code-block:: python

   helm push hello-world tutorial

Then, install the hello-world chart on the platform, go to the helm_chart directory and execute:

.. code-block:: python

   # depending on the helm version
     helm install --version 1.0 hello-world tutorial/hello-world
   #  or
     helm install --name hello-world --version 1.0 tutorial/hello-world

Go to :code:`IP-> System -> Kubernetes -> and verify` helm hello-world is running.

**To See all deployments:**

.. code-block:: python

   helm ls

Go to :code:`<INSTANCE_IP>/hello-world` and see if the application was deployed successfully

**To delete the helm chart again:**

.. code-block:: python


   # depending on the helm version
     helm delete hello-world
   # or
     helm delete --purge hello-world


