.. _api_operators:

Operators
=========
This section 


Base operators
--------------

Base operators are used as base classes for task specific operators.

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

We have multiple operators that can handle and manage dicom data on the platform. 
You can use these operators e.g. to modify dicom tags, to send or delete dicom data within the internal PACS or to resample dicom data.
Most of these operators take dicom data as input.

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

ZipUnzipOperator
*****************

.. automodule:: kaapana.operators.ZipUnzipOperator
   :members:
   :undoc-members:
   :show-inheritance:


   