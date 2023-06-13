.. _user_guide_fs:

First Steps (TODO: copy sections from here)
*******************************************

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



..#TODO
Uploading images into the platform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are two ways of getting images into the platform either sending them directly via DICOM (which is the preferred way) or uploading them via the web browser (currently an experimental feature). Detailed instructions are also available in the *Data Upload* wizard page within the *Workflows* menu of the web interface.

.. note::
  When DICOM data is sent to the DICOM receiver of the platform two things happen.:

  #. The incoming data is **saved to the local PACS system**
  #. **Metadata** of the incoming data is extracted and indexed to allow fast filtering and querying via the *Meta Dashboard* or the *Datasets View*.

Option 1: Sending images via DICOM DIMSE (preferred)
"""""""""""""""""""""""""""""""""""""""""""""""""""""

Images can directly be send via DICOM DIMSE to the DICOM receiver port ``11112`` of the platform.
If you have images locally you can use e.g. `DCMTK <https://dicom.offis.de/dcmtk.php.en>`_.
However, any tool that sends images to a DICOM receiver can be used. 

Here is an example of sending images with DCMTK:
::
  dcmsend -v <ip-address of server> 11112  --scan-directories --call <aetitle of images, used for filtering> --scan-pattern '*'  --recurse <data-dir-of-DICOM images>

.. hint::
    | The called AE title is used to specify the dataset which groups the data for later filtering. If the dataset already exist on the platform the new images will be appended.

Option 2: Uploading images via the Web Interface (experimental)
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

To upload images via the webfrontend, visit the *Data Upload* wizard page within the *Workflows* menu of the Web interface and follow the steps described in the wizard. Make sure to check the information how uploaded data should be formatted which is provided within the wizard.


.. hint::
    | The upload via the web interface allows to upload **NIfTI** data.


..#TODO: this is probably already a duplicate of faq_howto_remove_data
Deleting images from the platform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The imaging data is saved in the internal PACS and its metadata in OpenSearch. A workflow called ``delete-series-from-platform`` is provided to delete data from those locations and thus removes it completely from the platform.

#. Open the *Datasets* View in the *Workflows* menu and select the dataset containing the images which should be deleted
#. Press the ``Start Workflow`` button (the one with the Play symbol) and start the ``delete-series-from-platform`` workflow.
#. In the ``Workflow List`` the status of the deletion can be observed. Once the workflow has successfully ended the images are deleted from the platform.

For more information check out the documentation of the workflow at :ref:`faq_howto_remove_data`.


..#TODO: Note that one sentence OHIF description is moved to the end of store.rst
Viewing and Exploring images
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. _creating-datasets:

Datasets View
"""""""""""""

The *Datasets* View within the *Workflows* menu provides an overview of the images stored on the platform as well as statistics about their metadata. Individual images can be inspected in more detail by either double-clicking or using the eye symbol which opens a detail view including metadata as well as a volume viewer. From the Detail view there is also a link provided to directly jump into the OHIF viewer which is the main DICOM Viewer in the platform. By using the *Start Workflow* button (the one with the play symbol) workflows can be started directly from this view.



..#TODO: probably also explained in WMS

.. _processing_stack:

Processing
----------

Data uploaded to the platform is processed within *Workflows*. The execution of this workflows is managed by a workflow management system which in Kaapana is Airflow. In Airflow a workflow is called a DAG (directed acyclic graph) and it consists of operators which perform the actual work. Airflow takes care that the operators of a workflow are executed in the correct order and allows scheduling and error handling necessary to process images at scale. Operators can also be shared between workflows and therefore provide building-blocks for reoccurring tasks in workflows (the :ref:`operators` provides an overview of the available operators).

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


..#TODO
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




