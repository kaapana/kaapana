.. _platform_user_guide_fs:

First Steps
***********

This manual is intended to provide a quick and easy way to get started with the :term:`kaapana-platform`. In detail, after given default configurations we will introduce the storage,
the processing and the core stack of the platform and show examples of how to use them.

.. attention::
    | Kaapana should not be considered a finished platform or software.


Default configuration
---------------------

Default credentials
^^^^^^^^^^^^^^^^^^^

 ============================ ============== ============
  Component                    Username       Password   
 ============================ ============== ============
  **Kaapana Login**            kaapana        kaapana    
  **Keycloak Administrator**   admin          Kaapana2020
  **Minio**                    kaapanaminio   Kaapana2020
  **Grafana**                  admin          admin      
 ============================ ============== ============

.. hint::
    | Most likely you will not need the Minio admin password. Use the ``Login with OpenID`` instead.  


Port Configuration
^^^^^^^^^^^^^^^^^^
In the default configuration the following ports are opened for incoming traffic on the system

======= ========== =================================================================
 Port    Protocol   Description
======= ========== =================================================================
    80   HTTP       Redirect to HTTPS port 443
   443   HTTPS      Web Interface of the Platform (Interaction, File Upload, APIs)
 11112   DIMSE      DICOM C-STORE SCP to send images to the platform
======= ========== =================================================================

.. attention::
    | Kaapana uses MicroK8s as Kubernetes distribution which also opens ports on the machine it runs on. For an up to date list visit `the corresponding microk8s documentation <https://microk8s.io/docs/services-and-ports>`_.

.. _storage-stack:

Storage
-------

In general, the platform is a processing platform, which means that it is not a persistent data storage. Ideally, all the data on the platform should only form a copy of the original data.
Data that is in DICOM format is stored in an internal PACS called  *DCM4CHEE*.
For all non-DICOM data, an object store called *Minio* is available.
In Minio, arbitrary data files can be stored in buckets and are accessible via the browser for download.
Ideally the results of a workflow executed on the platform will be available as DICOM and stored in the PACS of the Platform where it can be accessed by via the existing tooling (e.g. Datasets View, Meta Dashboard).
However the DICOM format might not always be a good fit for results, therefore non-DICOM results are supported via Minio.
Sending DICOM images to platform (e.g. from a clinical PACS or a radiologists workstation) is possible via port ``11112``. Here a component called *Clinical Trial Processor (CTP)* takes care of receiving the images and then triggers the ingestion workflows.

If you are more interested in the technologies, you can get started here:

* `OpenSearch <https://opensearch.org/>`_
* `OpenSearch Dashboards <https://opensearch.org/docs/latest/dashboards/index/>`_
* `Minio <https://min.io/>`_
* `OHIF <https://ohif.org/>`_
* `Clinical Trial Processor (CTP) <https://mircwiki.rsna.org/index.php?title=CTP-The_RSNA_Clinical_Trial_Processor#Clinical_Trial_Processor_.28CTP.29>`_


Uploading images into the platform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are two ways of getting images into the platform either sending them directly via DICOM (which is the preferred way) or uploading them via the web browser (currently an experimental feature). Detailed instructions are also available in the *Data Upload* wizard page within the *Workflows* menu of the web interface.

.. note::
  When DICOM data is sent to the DICOM receiver of the platform two things happen.:

  #. The incoming data is **saved to the local PACS system**
  #. **Metadata** of the incoming data is extracted and indexed to allow fast filtering and querying via the *Meta Dashboard* or the *Datasets View*.

Option 1: Sending images via DICOM DIMSE (preferred)
"""""""""""""""""""""""""""""""""""""""""""""""""""

Images can directly be send via DICOM DIMSE to the DICOM receiver port ``11112`` of the platform.
If you have images locally you can use e.g. `DCMTK <https://dicom.offis.de/dcmtk.php.en>`_.
However, any tool that sends images to a DICOM receiver can be used. 

Here is an example of sending images with DCMTK:
::
  dcmsend -v <ip-address of server> 11112  --scan-directories --call <aetitle of images, used for filtering> --scan-pattern '*'  --recurse <data-dir-of-DICOM images>

.. hint::
    | The called AE title is used to specify the dataset which groups the data for later filtering. If the dataset already exist on the platform the new images will be appended.

Option 2: Uploading images via the Web Interface (experimental)
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

To upload images via the webfrontend, visit the *Data Upload* wizard page within the *Workflows* menu of the Web interface and follow the steps described in the wizard. Make sure to check the information how uploaded data should be formatted which is provided within the wizard.


.. hint::
    | The upload via the web interface allows to upload **NIfTI** data.



Deleting images from the platform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The imaging data is saved in the internal PACS and its metadata in OpenSearch. A workflow called ``delete-series-from-platform`` is provided to delete data from those locations and thus removes it completely from the platform.

#. Open the *Datasets* View in the *Workflows* menu and select the dataset containing the images which should be deleted
#. Press the ``Start Workflow`` button (the one with the Play symbol) and start the ``delete-series-from-platform`` workflow.
#. In the ``Workflow List`` the status of the deletion can be observed. Once the workflow has successfully ended the images are deleted from the platform.

For more information check out the documentation of the workflow at :ref:`extensions delete`.


Viewing and Exploring images
^^^^^^^^^^^^^^^^^^^^^^^^^^^^


.. _creating-datasets:

Datasets View
"""""""""""""

The *Datasets* View within the *Workflows* menu provides an overview of the images stored on the platform as well as statistics about their metadata. Individual images can be inspected in more detail by either double-clicking or using the eye symbol which opens a detail view including metadata as well as a volume viewer. From the Detail view there is also a link provided to directly jump into the OHIF viewer which is the main DICOM Viewer in the platform. By using the *Start Workflow* button (the one with the play symbol) workflows can be started directly from this view.

OHIF DICOM Viewer
"""""""""""""""""

DICOM Images can also be viewed directly in the OHIF Viewer. It can be found as *OHIF* under the *Store* menu.


Meta-Dashboard
""""""""""""""

When the focus is more on metadata than visually inspecting the image data directly the *Meta-Dashboard* might be useful. It provides aggregated visualizations for the metadata of the images in the platform and can be used to define datasets based on metadata queries. The Dashboard can be found as *Meta-Dashboard* under the *Meta* menu.


.. _processing-stack:

Processing
----------

Data uploaded to the platform is processed within *Workflows*. The execution of this workflows is managed by a workflow management system which in Kaapana is Airflow. In Airflow a workflow is called a DAG (directed acyclic graph) and it consists of operators which perform the actual work. Airflow takes care that the operators of a workflow are executed in the correct order and allows scheduling and error handling necessary to process images at scale. Operators can also be shared between workflows and therefore provide building-blocks for reoccurring tasks in workflows (the :ref:`api_documentation_root` provides an overview of the available operators).

.. hint::
  Airflow operators are in general implement as containers which are executed in the underlying Kubernetes cluster. When Airflow executes an operator within Kaapana it creates a Kubernetes Job object which then executes the actual container. The Job objects performing the actual processing on the Kubernetes cluster are grouped within the ``jobs`` namespace.

A detailed overview of the concepts of Airflow can be found `in their documentation <https://airflow.apache.org/docs/stable/concepts.html>`_.

If you are more interested in the technologies, you can get started here:

* `Airflow <https://airflow.apache.org/docs/stable/tutorial.html>`_
* `Kubernetes <https://kubernetes.io/docs/concepts/>`_


Execute workflows
^^^^^^^^^^^^^^^^^

Workflows are executed on dataset which contain the data the workflow should process.
Datasets can be created using the *Datasets View* or the Meta-Dashboard (see :ref:`creating-datasets`).
A workflow can then be executed either directly via the *Dataset View* or via the *Workflow Execution* dialog in the *Workflows* menu.
After a workflow is selected in the *Workflow Execution* dialog the user the dialog automatically extends and asks all the parameters necessary to run the workflow including the dataset.
After clicking the *Start Workflow* button on the end the workflow is triggered within Airflow and it appears in the *Workflow List* within the *Workflows* menu.
Here the execution of the workflow can be monitored. If things are not working as expected the *Workflow List* provides links to jump directly into the Airflow Web Interface where the issue can be investigated in more detail.

.. hint::
  | Check out the difference between :term:`single file and batch processing` 


Debugging
^^^^^^^^^

This short section will show you how to debug in case a workflow throws an error.

Syntax errors
"""""""""""""

If there is a syntax error in the implementation of a DAG or in the implementation of an operator, the errors are normally shown directly at the top of the Airflow DAGs view in red.
For further information, you can also consult the log of the container that runs Airflow. For this, you have to go to Kubernetes, select the namespace ``services`` and click on the Airflow pod.
On the top right there is a button to view the logs. Since Airflow starts two containers at the same time, you can switch between the two outputs at the top in 'Logs from...'.


Operator errors during execution
""""""""""""""""""""""""""""""""

* Via Workflow List: When you click on the red bubble within the workflow list all failed workflow runs will appear underneath the workflow. Within the 'Logs' column you can see two buttons linking directly to the logs in airflow and to the task view.
* Via Airflow: when you click in Airflow on the DAG you are guided to the 'Graph View'. Clicking on the red, failed operator a pop-up dialog opens where you can click on 'View Log' to see what happened.
* Via Kubernetes: in the namespace ``jobs``, you should find the running pod that was triggered from Airflow. Here you can click on the logs to see why the container failed. If the container is still running, you can also click on 'Exec into pod' to debug directly into the container.

After you resolved the bug in the operator, you can either restart the whole workflow or you can click on the operator in the 'Graph View', select 'Clear' in the pop-up dialog and confirm the next dialog.
This will restart the operator.



Kaapana Core
------------

After a practical introduction in the platform this section provides a view in the engine room of the Kaapana platform.
The core of the platform is a Kubernetes cluster, which is a container-orchestration system managing all the containers the platform consists of.
To manage the Kubernetes deployments a tool called Helm is used.
Ingress into the platform is managed by Traefik which serves as reverse proxy.
OAuth2-Proxy and Keycloak are used for access control and user management.
To provide a coherent interface the *landing page* wraps all of the services into one uniform web interface.


To find out more about the technologies checkout:

* `Helm <https://helm.sh/>`_
* `Kubernetes <https://kubernetes.io/docs/concepts/>`_
* `Grafana <https://grafana.com/>`_
* `Traefik <https://doc.traefik.io/traefik/>`_
* `Keycloak <https://www.keycloak.org/documentation.html>`_


Extending Kaapana
^^^^^^^^^^^^^^^^^

The capabilities of Kaapana can be extended using extensions. Extensions can add new workflows as well as new services to the platform by the click of an button in the web interface.
The *Extensions* menu in the web interface works like an app store, where new services and workflows can be installed and managed.

Under the hood, extensions are wrapped in Helm Charts which are installed and uninstalled via the web interface.
Containers of the extensions can mount data from the platform (e.g. Minio Buckets) directly. This allows extensions to directly work with data generated in a workflow.
For example, it is possible to trigger ``download-selected-files`` workflow to download images to Minio and then view the data by launching an MITK-Volume instance via the *Extensions* List.
In the :ref:`processing_dev_guide` you will learn how to write and add your own extensions.



User Management
^^^^^^^^^^^^^^^

Keycloak is an open source identity and access management solution that we integrated in our platform to manage authentication and different user roles. 
It can be accessed via *System* menu in the web interface.

Currently there are two user roles: The **admin** has some more privileges than a normal **user**, i.e. a **user** can not access the Kubernetes dashboard and can not see all components on the landing page.

.. hint::
    Keycloak provides various options to integrate with your environment. Please check out the `documentation of Keycloak <https://www.keycloak.org/documentation.html>`_ for more details.

Here two examples how user management can be done with Keycloak:
* **Adding a user manually**: Once you are logged in you can add users in the section **Users**. By selecting a user you can change i.e. the password in the tab **Credentials** or change the role under **Role mappings**. Try i.e. to add a user who has no admin rights, only user rights. 
* **Connecting an Active Directory**: In order to connect to an active directory go to the tap **User Federation**. Depending on your needs select *ldap* or *kerberos*. The necessary configuration you should be able to get from your institution. If everything is configured correctly you are able to login with the credentials from the Active Directory.



Monitoring
^^^^^^^^^^

In order to monitor whats the current status of the Kaapana platform a monitoring stack consisting of `Prometheus <https://prometheus.io/>`_ and `Grafana <https://grafana.com/>`_. Prometheus stores various metrics in the form of time series which can be displayed via Grafana. Grafana can be accessed via the *System* menu. Here things like disk space, CPU and GPU memory usage or network pressure can be visually inspected.


Kubernetes
^^^^^^^^^^

As mentioned above, Kubernetes is at heart of the whole platform. You can interact with Kubernetes either via the Kubernetes Dashboard, accessible on the *System* menu in the web interface or directly via the terminal using `kubectl` on the server. In case anything on the platform is not working, Kubernetes is the first place to go.


Examples how to debug with Kubernetes
"""""""""""""""""""""""""""""""""""""

Here are two examples, when you might need to access Kubernetes:

**Case 1: A Service is down**

In case you can't access a resource anymore, most probably a Pod within Kubernetes is down. To check whats causing the pod to fail you go to the Kubernetes-Dashboard. Select at the top a Namespace and then click on Pods. The pod which is down should appear in a red/orange color. Click on the pod. At the top right, you see four buttons. First click on the left one, this will show the logs of the container. In the best case you see here, why your pod is down. To restart the pod you need to simply delete the pod. In case it was not triggered by an Airflow-Dag it should restart automatically (The same steps can be done via the console, see below). In case the component/service crashes again, there might be some deeper error.

**Case 2: Platform is not responding**

When the whole platform does not respond this can have different reasons.

- Pods are down: In order to check if and which pods are down please log in to your server, and check which pods are down executing:

::

    kubectl get pods -A


If not all pods are running, a first try would be to delete the pod manually. It will then be automatically restarted. To delete a pod via the console. You need do copy the "NAME" and remember the NAMESPACE of the pod you want to delete and then execute:
::

    kubectl delete pods -n <THE NAMESPACE> <NAME OF THE POD>

If all pods are running, most probably there are network errors. This is usually caused by configuring a wrong server domain name during the deployment of the platform.

