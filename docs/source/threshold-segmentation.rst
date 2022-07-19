Provide a workflow as an extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Aim:** We will write a segmentation workflow that applies Otsu's method to create a segmentation of DICOM data.
We want to provide this workflow as an extension to the kaapana platform.

**Requirements:** You need the image `local-image/dag-installer:0.1.0` available in order to build the image for the DAG.

Step 1: Build an image for the proccessing algorithm
---------------------------------------

* Create a directory for the proccessing algorithm 
::

    mkdir -p threshold-segmentation/proccessing-containers/otsus-method/files/

* In the :code:`files` directory create a file called `otsus_method.py` that contains the segmentation algorithm based on Otsu's method:

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/treshold-segmentation/processing-containers/otsus-method/files/otsus_method.py

* In the :code:`otsus-method` directory create a :code:`Dockerfile` with the content:

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/treshold-segmentation/processing-containers/otsus-method/Dockerfile

Starting this container will execute the segmentation algorithm.

* Tag the image and push it to the registry

.. hint:: 
    If not already done, you have to login to your Docker registry via :code:`sudo docker login <docker-registry>/<docker-repo>`.


Inside the :code:`otsus-method` directory run 

::

    docker build -t <docker-registry>/<docker-repo>/threshold-segmentation:0.1.0 .
    docker push <docker-registry>/<docker-repo>/threshold-segmentation:0.1.0

Step 2: Create an image for the DAG 
-----------------------------------

* Create the folder for the DAG image. Inside the :code:`threshold-segmentation` directory run

::

    mkdir -p extension/docker/files/otsus-method

* Inside the folder :code:`extension/docker/files/otsus-method` create the :code:`OtsusMethodOperator.py` file

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/treshold-segmentation/extension/docker/files/otsus-method/OtsusMethodOperator.py

* Create a python file :code:`dag_example_thresholding_segmentation.py` for the DAG in the folder :code:`extension/docker/files/`

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/treshold-segmentation/extension/docker/files/dag_example_otsus_method.py
.. hint:: 
    The DAG will perform the following steps:
    Get the dicom files (LocalGetInputDataOperator) 
    >> convert the dicom files to .nrrd files  (DcmConverterOperator) 
    >> apply the segmentation (OtsusMethodOperator) 
    >> create a dicom segmentation from the .nrrd segmentation (Itk2DcmSegOperator ) 
    >> send the data back to the PACS (DcmSendOperator) 
    >> clean the workflow dir (LocalWorkflowCleanerOperator)

    **Note:** If you want to use this DAG as a template for your own segmentation algorithm note that 
    :code:`Itk2DcmSegOperator` requires the arguments :code:`segmentation_operator` and
    :code:`single_label_seg_info`.

* In :code:`extension/docker/` create the :code:`Dockerfile` for the DAG

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/treshold-segmentation/extension/docker/Dockerfile

.. hint:: 
    The base image :code:`local-only/dag-installer:0.1.0` scans all .py files in :code:`tmp` for images and pulls them via the Helm API.
    It also copies files into desired locations.

* Tag the image and push it to the registry. Next to the :code:`Dockerfile` in :code:`extension/docker/` run 

::

    docker build -t <docker-registry>/<docker-repo>/dag-example-otsus-method:kp_0.1.3__0.1.0 .
    docker push <docker-registry>/<docker-repo>/dag-example-otsus-method:kp_0.1.3__0.1.0

.. important:: 
    Setting the correct version tag is important, because the platform pulls the DAG with a specific version tag.
    This tag is build as follows: :code:`<platform-abbr>_<platform-version>__<dag-version>`.
    The :code:`platform-abbr` for the kaapana-platform is ``kp`` and for the starter-platform ``sp``.
    The :code:`platform-version` can be found at the bottom of the user interface.
    The :code:`dag-version` is specified in the :code:`Dockerfile` of the DAG.


Step 3: Create the helm chart
-----------------------------

* Create a folder for the chart. Inside :code:`treshold-segmentation/extension/` run 
:: 

    mkdir -p threshold-segmentation-workflow
    cd threshold-segmentation-workflow

* Create a file :code:`Chart.yaml`

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/treshold-segmentation/extension/threshold-segmentation-workflow/Chart.yaml
* Create a file :code:`requirements.yaml`

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/treshold-segmentation/extension/threshold-segmentation-workflow/requirements.yaml

.. important:: 
    The field :code:`repository` must be the relative path from the file :code:`requirements.yaml` to the directory that contains the 
    :code:`Chart.yaml` file for the dag-installer chart. This file is located in the subdirectory :code:`services/utils/dag-installer/dag-installer-chart/`
    of the kaapana repository.

* Create a file :code:`values.yaml`

.. literalinclude:: ../../templates_and_examples/examples/proccessing-pipelines/treshold-segmentation/extension/threshold-segmentation-workflow/values.yaml

.. hint:: 
    These three files define the helm chart that will be installed on the platform in order to provide the algorithm as a workflow.

* Update helm dependencies and package the chart 

::

    helm dep up 
    helm package .

This will create the file :code:`example-threshold-segmentation-workflow-0.1.0.tgz`

Step 4.1: Add the extension manually to the platform
-----------------------------------------------------

.. hint:: 
    This approach requires root permissions on the host server of the platform.

The easiest way to get the extension into the platform is by copying the packaged helm chart to the right location.
To do so you need access to the host machine, where the platform is running.
Just copy the file :code:`example-threshold-segmentation-workflow-0.1.0.tgz` into the subdirectory :code:`extensions/`
of the :code:`FAST_DATA_DIR` which is by default :code:`/home/kaapana/`. The :code:`FAST_DATA_DIR` can be set to another value in the :code:`install_platform.sh`
script before installation of the platform.

.. hint:: 
    This approach has the disadvantage that the extension only exists in the platform that is deployed on this host machine.
    If you want to provide your algorithm on another platform instance, you have to repeat this step again.
    Step 4.2 shows a persistent approach, where your algorithm is available for each platform that is installed from your private registry.


Step 4.2: (Persistent alternative) Update the :code:`kaapana-extension-collection` chart
----------------------------------------------------------------------------------------

The kaapana repository contains a special ***collection*** chart that depends on a list of other charts required for kaapana.
We will add the chart of our new DAG to this list and update the dependencies.

* Adjust the file :code:`collections/kaapana-collection/requirements.yaml` in your kaapana repository

::

    - name: example-threshold-segmentation-workflow
      version: 0.1.0
      repository: file://../../templates_and_examples/examples/proccessing-pipelines/treshold-segmentation/extension/threshold-segmentation-workflow/

.. hint:: 
    The repository field must point from the :code:`kaapana-extension-collection` chart to the directory of the chart for the DAG.

* Update the dependencies 

:: 

    helm dep up 

* Build and push the image 
  
::

    docker build -t <docker-registry>/<docker-repo>/kaapana-extension-collection:kp_0.1.3__0.1.0
    docker push <docker-registry>/<docker-repo>/kaapana-extension-collection:kp_0.1.3__0.1.0

* Restart the :code:`kaapana-extension-collection` pod 
  
One way to restart the pod is to click on the cloud button next to **Applications and workflows** in the Extension page.

You can also manually delete the pod on your host machine.
First search for the name of the pod.

:: 
    kubectl get pods -n default

The name of the pod begins with :code:`copy-kube-helm-collections`
Then delete the pod 

:: 
    kubectl delete pod <pod-name>

This will automatically download a new version of the chart and start a new pod.

