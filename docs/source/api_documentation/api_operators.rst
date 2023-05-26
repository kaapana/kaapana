.. _api_operators:

Operators
=========
This section 


Base operators
--------------

Base operators serve as foundational classes for task-specific operators.
When developing your own customized operator leverage these operators as base classes.

KaapanaBaseOperator
***********************

.. automodule:: kaapana.operators.KaapanaBaseOperator
   :members:
   :undoc-members:
   :show-inheritance:

KaapanaPythonBaseOperator
****************************

.. automodule:: kaapana.operators.KaapanaPythonBaseOperator
   :members:
   :undoc-members:
   :show-inheritance:

KaapanaApplicationOperator
******************************

.. automodule:: kaapana.operators.KaapanaApplicationOperator
   :members:
   :undoc-members:
   :show-inheritance:


DICOM operators
--------------------------

We provide a range of operators designed to handle and manage DICOM data efficiently. 
These operators offer various capabilities, such as modifying DICOM tags, generating DICOM data from binaries or JSON, and much more.

Bin2DcmOperator
****************

.. automodule:: kaapana.operators.Bin2DcmOperator
   :members:
   :undoc-members:
   :show-inheritance:

DcmConverterOperator
*********************

.. automodule:: kaapana.operators.DcmConverterOperator
   :members:
   :undoc-members:
   :show-inheritance:

DcmModifyOperator
******************

.. automodule:: kaapana.operators.DcmModifyOperator
   :members:
   :undoc-members:
   :show-inheritance:

DcmSeg2ItkOperator
********************

.. automodule:: kaapana.operators.DcmSeg2ItkOperator
   :members:
   :undoc-members:
   :show-inheritance:

Json2DcmSROperator
**********************

.. automodule:: kaapana.operators.Json2DcmSROperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalDcm2JsonOperator
************************

.. automodule:: kaapana.operators.LocalDcm2JsonOperator
   :members:
   :undoc-members:
   :show-inheritance:


Mask2nifitiOperator
**********************

.. automodule:: kaapana.operators.Mask2nifitiOperator
   :members:
   :undoc-members:
   :show-inheritance:

Pdf2DcmOperator
*******************

.. automodule:: kaapana.operators.Pdf2DcmOperator
   :members:
   :undoc-members:
   :show-inheritance:

NIFTI and nrrd operators
--------------------------

We offer operators specifically designed for NIFTI and nrrd data, enabling functionalities such as radiomics, resampling, and more.

CombineMasksOperator
**********************

.. automodule:: kaapana.operators.CombineMasksOperator
   :members:
   :undoc-members:
   :show-inheritance:

PyRadiomicsOperator
*********************

.. automodule:: kaapana.operators.PyRadiomicsOperator
   :members:
   :undoc-members:
   :show-inheritance:

ResampleOperator
*****************

.. automodule:: kaapana.operators.ResampleOperator
   :members:
   :undoc-members:
   :show-inheritance:

Itk2DcmSegOperator
********************

.. automodule:: kaapana.operators.Itk2DcmSegOperator
   :members:
   :undoc-members:
   :show-inheritance:

Store operators (MinIO and PACS)
-------------------------------------

You can utilize existing operators to communicate with the MinIO storage and the interal PACS of Kaapana.
Use these operators e.g. to send, retrieve or delete data.

DcmSendOperator
******************

.. automodule:: kaapana.operators.DcmSendOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalCtpQuarantineCheckOperator
********************************

.. automodule:: kaapana.operators.LocalCtpQuarantineCheckOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalDeleteFromPacsOperator
*****************************

.. automodule:: kaapana.operators.LocalDeleteFromPacsOperator
   :members:
   :undoc-members:
   :show-inheritance: 

LocalDicomSendOperator
***********************

.. automodule:: kaapana.operators.LocalDicomSendOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalGetRefSeriesOperator
****************************

.. automodule:: kaapana.operators.LocalGetRefSeriesOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalMinioOperator
*******************

.. automodule:: kaapana.operators.LocalMinioOperator
   :members:
   :undoc-members:
   :show-inheritance: 


Workflow management operators
------------------------------

This section comprises commonly used operators for obtaining input data and performing workflow directory cleanup. 
Additionally, it includes specialized operators for automatically triggering workflows and synchronizing the Airflow API with the DAGs available in the file system.

LocalAutoTriggerOperator
**************************

.. automodule:: kaapana.operators.LocalAutoTriggerOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalGetInputDataOperator
***************************

.. automodule:: kaapana.operators.LocalGetInputDataOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalServiceSyncDagsDbOperator
********************************

.. automodule:: kaapana.operators.LocalServiceSyncDagsDbOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalWorkflowCleanerOperator
******************************

.. automodule:: kaapana.operators.LocalWorkflowCleanerOperator
   :members:
   :undoc-members:
   :show-inheritance:


Opensearch operators
----------------------

Utilize the following operators to establish communication with Opensearch and effectively manage metadata information.

LocalDeleteFromMetaOperator
****************************

.. automodule:: kaapana.operators.LocalDeleteFromMetaOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalJson2MetaOperator
**************************

.. automodule:: kaapana.operators.LocalJson2MetaOperator
   :members:
   :undoc-members:
   :show-inheritance:


File management operators
---------------------------

This is a collection of operators that can be utilized for various file-based operations.

ZipUnzipOperator
*****************

.. automodule:: kaapana.operators.ZipUnzipOperator
   :members:
   :undoc-members:
   :show-inheritance:


   