.. _platform_user_guide_fs:

First Steps
***********

This manual is intended to provide a quick and easy way to get started with the :term:`kaapana-platform`. In detail, after given default configurations we will introduce the storage,
the processing and the core stack of the platform and show examples of how to use them.

.. hint::
    | This project should not be considered a finished platform or software. 


Default configuration
---------------------

Default credentials
^^^^^^^^^^^^^^^^^^^

**Main Kaapana Login:**
  | username: kaapana
  | password: kaapana

**Keycloak Usermanagement Administrator:**
  | username: admin
  | password: Kaapana2020

**Minio:**
  | username: kaapanaminio
  | password: Kaapana2020

Most likely you will not need the Minio admin password. Use the ``Login with OpenID`` instead.

Port Configuration
^^^^^^^^^^^^^^^^^^
In the default configuration only four ports are open on the server:

1. Port  **80**:   Redirects to https port 443

2. Port **443**:   Main https communication with the server

3. Port **11112**: DICOM receiver port, which should be used as DICOM node in your pacs

4. Port **6443**:  Kubernetes API port -> used for external kubectl communication and secured via the certificate

.. _storage-stack:

Storage stack: OpenSearch, OHIF and DCM4CHEE
--------------------------------------------

In general, the platform is a processing platform, which means that it is not a persistent data storage. Ideally, all the data on the platform should only form a copy of the original data.
Data that are in DICOM format are stored in an internal PACS called  DCM4CHEE. For all non-dicom data, an object store called Minio is available. In Minio, data are stored in buckets and are accessible via the browser for download.
Most of the results that are generated during a pipeline will be saved in Minio. Finally a component called Clinical Trial Processor (CTP) was added to manage the distribution and acceptance of images.
It opens the port ``11112`` on the server to accept DICOM images directly from, e.g. a clinic PACS.

If you are more interested in the technologies, you can get started here:

* `OpenSearch <https://opensearch.org/>`_
* `OpenSearch Dashboards <https://opensearch.org/docs/latest/dashboards/index/>`_
* `Minio <https://min.io/>`_
* `OHIF <https://ohif.org/>`_
* `Clinical Trial Processor (CTP) <https://mircwiki.rsna.org/index.php?title=CTP-The_RSNA_Clinical_Trial_Processor#Clinical_Trial_Processor_.28CTP.29>`_


Getting images into the platform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order to get started with the platform, first you will have to send images to the platform. There are two ways of getting images into the platform:

(1) The preferred way is to use the provided DICOM receiver on port ``11112``. If you have images locally you can use e.g. `DCMTK <https://dicom.offis.de/dcmtk.php.en>`_.
However, any tool that sends images to a DICOM receiver can be used. 

Here is an example of sending images with DCMTK:

::

   dcmsend -v <ip-address of server> 11112  --scan-directories --call <aetitle of images, used for filtering> --scan-pattern '*'  --recurse <data-dir-of-DICOM images>

The AE title should represent your dataset since we use it for filtering images on our Meta-Dashboard in OpenSearch Dashboards.

(2) Alternatively, you can upload DICOM images via the object store Minio, however, we only recommend this for small image sizes.
The upload in Minio expects a zip file of images with a ``.dcm`` ending. The zip file can be uploaded via drag&drop select ``Store``, select ``Minio``, select Minio Bucket ``uploads`` and drag & drop your zip file.


When DICOMs are sent to the DICOM receiver of the platform two things happen. Firstly, the DICOMs are saved in the local PACs system called DCM4CHEE. Secondly, 
the meta data of the DICOMs are extracted and indexed by a search engine (powered by OpenSearch) which makes the meta data available for OpenSearch Dashboards.
The OpenSearch dashboard called "Meta dashboard" is mainly responsible for visualizing the metadata but also serves as a filtering tool in order to select images and to trigger a processing pipeline.
Image cohorts on the Meta dashboard can be selected via custom filters at the top. To ease this process, it is also possible to add filters automatically by clicking on the graphs (``+/-`` pop ups).

Deleting images from the platform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Information of the images are saved in the PACS and in OpenSearch. A workflow called ``delete-series-from-platform`` is provided to delete images from the platform. Simply go to the Meta Dashboard,
select the images you want to delete and start the workflow. On the Airflow dashboard you can see when the DAG ``delete-series-from-platform`` has finished, then all your selected images should be deleted from the platform. For more information check out the documentation of the workflow at :ref:`extensions delete`.

Viewing images with OHIF
^^^^^^^^^^^^^^^^^^^^^^^^

A web-based DICOM viewer (OHIF) has been integrated to show images in the browser. The functionality of this viewer is limited at the moment, but more features will come soon. To view images, go to OHIF and click on the study.
When e.g. a segmentation is available you can visualize the segmentation by dragging it into the main window. 

.. _processing-stack:

Processing stack: Airflow, Kubernetes namespace ``flow-jobs`` and the working directory
---------------------------------------------------------------------------------------


In order to apply processing pipelines in which different operations are performed in a certain order to images, a framework is necessary which allows us to define and trigger such a pipeline. We decided to use Airflow for that. In Airflow, a workflow is called a DAG (directed acyclic graph, a graph type where you can only traverse forwards). It consists of operators which are the bricks of your pipeline. Ideally, every operator triggers a Docker container in which some kind of task is performed. A detailed overview of the concepts can be found `here <https://airflow.apache.org/docs/stable/concepts.html>`_.

Besides Airflow, Kubernetes is used to manage the Docker containers that are triggered by Airflow. On the platform, we introduce a namespace called ``flow-jobs`` in which all containers initiated by Airflow are started. 

If you are more interested in the technologies, you can get started here:

* `Airflow <https://airflow.apache.org/docs/stable/tutorial.html>`_
* `Kubernetes <https://kubernetes.io/docs/concepts/>`_

Triggering workflows with OpenSearch Dashboards
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As mentioned above, OpenSearch Dashboards visualizes all the metadata of the images and is therefore a good option to also filter the images to which a workflow should be applied.
To trigger a workflow from OpenSearch Dashboards, a panel ``trigger_workflow`` was added to the dashboard which contains a dropdown to select a workflow and a start button to trigger the configuration dialog for starting the workflow. The configuration dialog includes options specific to the chosen workflow and also some options which are available for most workflows, like choosing between single and batch execution.

.. hint::

  | Check out the difference between :term:`single file and batch processing` 

In order to trigger a workflow on images, filter the images to which you want to apply the pipeline, select the workflow (e.g. ``collect-metadata``) and press ``Start``. The workflow is then started by clicking ``Start`` again on the configuration popup dialog.

Once OpenSearch Dashboards has sent its request, the Airflow pipeline is triggered. If you navigate to Airflow, you should see that the DAG collect-meta data is running.
By clicking on the DAG you will see different processing steps, that are called ``operators``. 
In the operators, first the query of OpenSearch Dashboards is used to download the selected images from the local PACS system DCM4CHEE to a predefined directory of the server so that the images are available
for the upcoming operators (``get-input-data``), then the dicoms are anonymized (``dcm-anonmyizer``), the meta data are extracted and converted to jsons (``dcm2json``), the generated jsons are concatenated (``concatenated-metadata``),
the concatenated json is send to Minio (``minio-actions-put``) and finally, the local directory is cleaned again. You can check out the :ref:`processing_dev_guide` to learn how to write your own DAGs.
Also you can go to Minio to see if you find the collected meta data. 

Debugging
^^^^^^^^^

This short section will show you how to debug in case a workflow throws an error.

**Syntax errors**:

If there is a syntax error in the implementation of a DAG or in the implementation of an operator, the errors are normally shown directly at the top of the Airflow DAGs view in red.
For further information, you can also consult the log of the container that runs Airflow. For this, you have to go to Kubernetes, select the namespace ``flow`` and click on the Airflow pod.
On the top right there is a button to view the logs. Since Airflow starts two containers at the same time, you can switch between the two outputs at the top in 'Logs from…'.

**Operator errors during execution**:

* Via Airflow: when you click in Airflow on the DAG you are guided to the 'Graph View'. Clicking on the red, failed operator a popup opens where you can click on 'View Log' to see what happened.
* Via Kubernetes: in the namespace ``flow-jobs``, you should find the running pod that was triggered from Airflow. Here you can click on the logs to see why the container failed. If the container is still running, you can also click on 'Exec into pod' to debug directly into the container.

After you resolved the bug in the operator, you can either restart the whole workflow from OpenSearch Dashboards or you can click on the operator in the 'Graph View', select 'Clear' in the popup and confirm the next dialog.
This will restart the operator.

Core stack: Landing Page, Traefik, Louketo, Keycloak, Grafana, Kubernetes and Helm
----------------------------------------------------------------------------------

From a technical point of view the core stack of the platform is Kubernetes, which is a container-orchestration system managing all the docker containers.
Helm is the tool that we use to ship out our Kubernetes deployments. Traefik is a reverse proxy, managing the conversation between all components.
Louketo and Keycloak form the base for user authentication. Finally, the landing page wraps all of the services in :term:`kaapana-platform` into one uniform webpage.

To find out more about the technologies checkout:

* `Helm <https://helm.sh/>`_
* `Kubernetes <https://kubernetes.io/docs/concepts/>`_
* `Grafana <https://grafana.com/>`_
* `Traefik <https://doc.traefik.io/traefik/>`_
* `Keycloak <https://www.keycloak.org/documentation.html>`_

Launching extensions via the landing page
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On the landing page you can find a section called ``Extensions``. Extensions can be workflows (that are used in Airflow) or static applications like a Jupyter Notebook.
In general, the extensions can be understood like an app store, where new services and workflows can be installed and managed.
Under the hood, Helm Charts are installed and uninstalled via the GUI. Most of the applications that are launched mount the Minio directory,
so that you can directly work with the data that are generated in a workflow. In example, you can trigger the ``download-selected-files`` DAG to download images to Minio and then watch the data starting an MITK-Volume instance.
In the :ref:`processing_dev_guide` you will learn how to write and add your own extensions.

Keycloak: Add users to the platform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Keycloak is an open source identity and access management solution that we integrated in our platform to manage authentication and different user roles. 
You can access keycloak via the dashboard (only if you have admin rights) or directly via */auth/*.

Please check out the `documentation of Keycloak <https://www.keycloak.org/documentation.html>`_ to find out what Keycloak is capable of. Here is an example of how to add new users to the platform:

Depending on your needs you can add users manually or connect Keycloak instance i.e. to an Active Directory.

* **Adding a user manually**: Once you are logged in you can add users in the section **Users**. By selecting a user you can change i.e. his password in the tab **Credentials** or change his role under **Role mappings**.Try i.e. to add a user who has no admin rights, only user rights. Currently there are only two user roles. The **admin** has some more privileges than a normal **user**, i.e. a **user** can not access the Kubernetes dashboard and can not see all components on the landing page.
* **Connecting with an Active Directory**: In order to connect to an active directory go to the tap **User Federation**. Depending on your needs select *ldap* or *kerberos*. The necessary configuration you should be able to get from your institution. If everything is configured correctly you should be able to login with your credentials from the Active Directory.

Grafana and Prometheus
^^^^^^^^^^^^^^^^^^^^^^

As with all platforms, a system to monitor the current system status is needed.
To provide this, kaapana utilizes a commonly used combination of `Prometheus <https://prometheus.io/>`_ and `Grafana <https://grafana.com/>`_.
The graphical dashboards present states such as disk space, CPU and GPU memory usage, network pressure etc.


Kubernetes: Your first place to look if something does not work
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As mentioned above, Kubernetes is the basis of the whole platform. You can talk to Kubernetes either via the Kubernetes Dashboard, accessible on the landing page or via the terminal directly on your server. In case anything on the platform is not working, Kubernetes is the first place to go. Here are two use cases, when you might need to access Kubernetes.

**Case 1: Service is down**

In case you can't access a resource anymore most probably a Pod is down. In this case you first need to check why. For this you go to the Kubernetes-Dashboard. Select at the top a Namespace and then click on Pods. The pod which is down should appear in a red/orange color. Click on the pod. At the top right, you see four buttons. First click on the left one, this will show the logs of the container. In the best case you see here, why your pod is down. To restart the pod you need to simply delete the pod. In case it was not triggered by an Airflow-Dag it should restart automatically (The same steps can be done via the console, see below). In case the component/service crashes again, there might be some deeper error.

**Case 2: Platform is not responding**

When your platform does not respond this can have different reasons.

- Pods are down: In order to check if and which services are down please log in to your server, where you can check if pods are down with:

::

    kubectl get pods -A

If all pods are running, most probably there are network errors. If not, a first try would be to delete the pod manually. It will then be automatically restarted. To delete a pod via the console. You need do copy the "NAME" and remember the NAMESPACE of the pod you want to delete and then execute:
::

    kubectl delete pods -n <THE NAMESPACE> <NAME OF THE POD>

- Network errors: In case of network errors, there seems to be an error within your local network. E.g. your server domain might not work.

