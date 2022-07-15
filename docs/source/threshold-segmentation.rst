Provide a workflow as an extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Aim:** We will write a segmentation workflow that applies Otsu's method to create a segmentation of a DICOM.
We want to provide this workflow as an extension to the kaapana platform.
We assume we already have 

**Requirements:** You need the `local-image/dag-installer:0.1.0` image available.

Step 1: Build an image for the proccessing algorithm
---------------------------------------

* Create a directory for the proccessing algorithm 
::
    mkdir -p threshold-segmentation/proccessing-containers/otsus-method/files/

* In the :code:`files` directory create a file called `otsus_method.py` that contains the segmentation algorithm based on Otsu's method:

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/threshold-segmentation/proccessing-containers/otsus-method/files/otsus_method.py 

* In the :code:`otsus-method` directory create a :code:`Dockerfile` with the content:

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/threshold-segmentation/proccessing-containers/otsus-method/Dockerfile

Starting this container will execute the segmentation algorithm.

* Tag the image and push it to the registry

Inside the :code:`otsus-method` directory run 

::
    docker build -t <docker-registry>/<docker-repo>/threshold-segmentation:0.1.0 .
    docker push <docker-registry>/<docker-repo>/threshold-segmentation:0.1.0

.. hint:: 
    If not already done, you have to login to your Docker registry via :code:`sudo docker login <docker-registry>/<docker-repo>`.

Step 2: Create an image for the DAG 
-----------------------------------

* Create the folder for the DAG image 

Inside the :code:`threshold-segmentation` directory run

::
    mkdir -p extension/docker/files/otsus-method

* Create the dag python file named :code:`dag_example_thresholding_segmentation.py`in the folder:code:`files/`.

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/threshold-segmentation/extension/docker/files/dag_example_otsus_method.py 

.. hint:: 
    TODO Description of the DAG.
    TODO information about the :code:`Itk2DcmSegOperator`.

* Inside the folder :code:`extension/docker/files/otsus-method` create the :code:`OtsusMethodOperator.py` file.

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/threshold-segmentation/extension/docker/files/otsus-method/OtsusMethodOperator.py

* In :code:`extension/docker/``create the :code:`Dockerfile´`for the dag

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/threshold-segmentation/extension/docker/Dockerfile

.. hint:: 
    TODO explain the baseimage :code:`local-only/dag-installer:0.1.0`

* Tag the image and push it to the registry

Inside the :code:`docker` directory run 

::
    docker build -t <docker-registry>/<docker-repo>/dag-example-otsus-method:0.1.0 .
    docker push <docker-registry>/<docker-repo>/dag-example-otsus-method:0.1.0

Step 3: Create the helm chart

* Create a folder for the chart. Inside :code:`extension/` run 
:: 
    mkdir -p threshold-segmentation-workflow
    cd threshold-segmentation-workflow

* Create a file :code:`Chart.yaml`

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/threshold-segmentation/extension/threshold-segmentation-workflow/Chart.yaml

* Create a file :code:`requirements.yaml`

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/threshold-segmentation/extension/threshold-segmentation-workflow/requirements.yaml

* Create a file :code:`values.yaml`

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/threshold-segmentation/extension/threshold-segmentation-workflow/values.yaml

.. hint:: 
    TODO Describe Chart.yaml, requirements.yaml and values.yaml

* Update helm dependencies and package the chart 

::
    helm dep up 
    helm package .

This will create the file :code:`example-threshold-segmentation-workflow-0.1.0.tgz`

Step 4.1: Add the extension manually to the platform.

The easiest way to get the extension into the platform is by copying the packaged helm chart to the right location.
To do so you need access to the host machine, where the platform is running.
Just copy the file :code:`example-threshold-segmentation-workflow-0.1.0.tgz` into the subdirectory :code:`extensions/`
of the :code:`FAST_DATA_DIR` which is by default :code:`/home/kaapana/`, but can be set to another value in the :code:`install_platform.sh`
script before installation of the platform.

.. hint:: 
    TODO Disadvantage -> This is not persistent if your host machine crashes our you want to install kaapana on another machine.

Step 4.2: (Persistent alternative) Update the :code:`kaapana-extension-collection` chart

Following this approach includes the extension in the :code:`kaapana-extension-collection` chart and if you install the platform
on another machine from the same registry your extension will still be available.

* Adjust the file :code:`collections/kaapana-collection/requirements.yaml`

::
    - name: example-threshold-segmentation-workflow
      version: 0.1.0


* Update the dependencies 

:: 
    helm dep up 

* Build and push the image 
  
::
    docker build -t <docker-registry>/<docker-repo>/kaapana-extension-collection:kp_0.1.3__0.1.0
    docker push <docker-registry>/<docker-repo>/kaapana-extension-collection:kp_0.1.3__0.1.0

.. hint:: 
    TODO explain the vresion tagging convention

* Restart the :code:`kaapana-extension-collection` pod 
  
One way to restart the pod is to click on the cloud button next to **Applications and workflows** in the Extension page.

You can also manually delete the pod on your host machine via 

:: 
    kubectl delete TODO insert correct command

This will automatically download a new version of the pod and restart it

