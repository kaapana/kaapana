.. _api_operators:

Operators
=========

Not yet all operators are documented.
For the full picture, please have a look at the `kaapana.operators <https://github.com/kaapana/kaapana/tree/develop/data-processing/kaapana-plugin/extension/docker/files/plugin/kaapana/operators>`_ package in the code.


Base operators
--------------

Base operators serve as foundational classes for task-specific operators.
When developing your own customized operator leverage these operators as base classes.

KaapanaBaseOperator
^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.KaapanaBaseOperator
   :members:
   :undoc-members:
   :show-inheritance:

KaapanaPythonBaseOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.KaapanaPythonBaseOperator
   :members:
   :undoc-members:
   :show-inheritance:

KaapanaApplicationOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.KaapanaApplicationOperator
   :members:
   :undoc-members:
   :show-inheritance:


DICOM operators
--------------------------

We provide a range of operators designed to handle and manage DICOM data efficiently. 
These operators offer various capabilities, such as modifying DICOM tags, generating DICOM data from binaries or JSON, and much more.

Bin2DcmOperator
^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.Bin2DcmOperator
   :members:
   :undoc-members:
   :show-inheritance:

Dcm2MetaJsonConverter
^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.Dcm2MetaJsonConverter
   :members:
   :undoc-members:
   :show-inheritance:

DcmConverterOperator
^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.DcmConverterOperator
   :members:
   :undoc-members:
   :show-inheritance:

DcmModifyOperator
^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.DcmModifyOperator
   :members:
   :undoc-members:
   :show-inheritance:

DcmQueryOperator
^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.DcmQueryOperator
   :members:
   :undoc-members:
   :show-inheritance:

DcmSeg2ItkOperator
^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.DcmSeg2ItkOperator
   :members:
   :undoc-members:
   :show-inheritance:

Json2DcmSROperator
^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.Json2DcmSROperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalDcm2JsonOperator
^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.LocalDcm2JsonOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalDcmAnonymizerOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.LocalDcmAnonymizerOperator
   :members:
   :undoc-members:
   :show-inheritance:

Mask2nifitiOperator
^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.Mask2nifitiOperator
   :members:
   :undoc-members:
   :show-inheritance:

Pdf2DcmOperator
^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.Pdf2DcmOperator
   :members:
   :undoc-members:
   :show-inheritance:

File-based operators
---------------------------

This is a collection of operators that can be utilized for various file-based operations.

LocalConcatJsonOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.LocalConcatJsonOperator
   :members:
   :undoc-members:
   :show-inheritance:

ZipUnzipOperator
^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.ZipUnzipOperator
   :members:
   :undoc-members:
   :show-inheritance:

NIFTI and nrrd operators
--------------------------

We offer operators specifically designed for NIFTI and nrrd data, enabling functionalities such as radiomics, resampling, and more.

CombineMasksOperator
^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.CombineMasksOperator
   :members:
   :undoc-members:
   :show-inheritance:

Itk2DcmOperator
^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.Itk2DcmOperator
   :members:
   :undoc-members:
   :show-inheritance:

Itk2DcmSegOperator
^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.Itk2DcmSegOperator
   :members:
   :undoc-members:
   :show-inheritance:

PyRadiomicsOperator
^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.PyRadiomicsOperator
   :members:
   :undoc-members:
   :show-inheritance:

ResampleOperator
^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.ResampleOperator
   :members:
   :undoc-members:
   :show-inheritance:

Opensearch operators
----------------------

Utilize the following operators to establish communication with Opensearch and effectively manage metadata information.

LocalDeleteFromMetaOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.LocalDeleteFromMetaOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalJson2MetaOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.LocalJson2MetaOperator
   :members:
   :undoc-members:
   :show-inheritance:

Service operators
---------------------------

These operators are used in service DAGs which run automatically, e.g. if data arrives at the platform or nightly to perform a cleanup.

GenerateThumbnailOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.GenerateThumbnailOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalAddToDatasetOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.LocalAddToDatasetOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalAutoTriggerOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.LocalAutoTriggerOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalCleanUpExpiredWorkflowDataOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.LocalCleanUpExpiredWorkflowDataOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalCtpQuarantineCheckOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.LocalCtpQuarantineCheckOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalServiceSyncDagsDbOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.LocalServiceSyncDagsDbOperator
   :members:
   :undoc-members:
   :show-inheritance:

Store operators (MinIO and PACS)
-------------------------------------

You can utilize existing operators to communicate with the MinIO storage and the interal PACS of Kaapana.
Use these operators e.g. to send, retrieve or delete data.

DcmSendOperator
^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.DcmSendOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalDeleteFromPacsOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.LocalDeleteFromPacsOperator
   :members:
   :undoc-members:
   :show-inheritance: 

LocalDicomSendOperator
^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.LocalDicomSendOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalGetRefSeriesOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.LocalGetRefSeriesOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalMinioOperator
^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.LocalMinioOperator
   :members:
   :undoc-members:
   :show-inheritance: 

LocalTaggingOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.LocalTaggingOperator
   :members:
   :undoc-members:
   :show-inheritance:

Uncategorized operators
---------------------------

We have even more operators for different usecases.
Just take a look if there is something you can utilize in your own workflow.

LocalDagTriggerOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.LocalDagTriggerOperator
   :members:
   :undoc-members:
   :show-inheritance:

TrainTestSplitOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.TrainTestSplitOperator
   :members:
   :undoc-members:
   :show-inheritance:

Workflow management operators
------------------------------

This section comprises commonly used operators for obtaining input data, downloading models, and performing a workflow directory cleanup during the final step of a dag. 

GetZenodoModelOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.GetZenodoModelOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalGetInputDataOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.LocalGetInputDataOperator
   :members:
   :undoc-members:
   :show-inheritance:

LocalWorkflowCleanerOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kaapana.operators.LocalWorkflowCleanerOperator
   :members:
   :undoc-members:
   :show-inheritance: