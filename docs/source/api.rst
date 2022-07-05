.. _api:

API Documentation
=================

.. warning::
   This area is currently under construction and does not list all available operators. For the full picture, please have a look at the `kaapana.operators <https://github.com/kaapana/kaapana/tree/783ed051c4ad8feb865fc5c7d8b9dd21267287da/workflows/airflow-components/plugins/kaapana/operators>`_ package in the code.

Operators
---------

Base Operators
~~~~~~~~~~~~~~

.. automodule:: kaapana.operators.KaapanaBaseOperator
   :members:
   :undoc-members:
   :show-inheritance:


DICOM
~~~~~

.. automodule:: kaapana.operators.DcmSendOperator
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: kaapana.operators.DcmModifyOperator
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: kaapana.operators.LocalDicomSendOperator
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: kaapana.operators.LocalDeleteFromPacsOperator
   :members:
   :undoc-members:
   :show-inheritance: 

.. automodule:: kaapana.operators.LocalDeleteFromElasticOperator
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: kaapana.operators.Pdf2DcmOperator
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: kaapana.operators.ResampleOperator
   :members:
   :undoc-members:
   :show-inheritance:


Storage
~~~~~~~

.. automodule:: kaapana.operators.LocalMinioOperator
   :members:
   :undoc-members:
   :show-inheritance: 


Workflow Management
~~~~~~~~~~~~~~~~~~~

.. automodule:: kaapana.operators.LocalServiceSyncDagsDbOperator
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: kaapana.operators.LocalWorkflowCleanerOperator
   :members:
   :undoc-members:
   :show-inheritance:


File Management
~~~~~~~~~~~~~~~~

.. automodule:: kaapana.operators.ZipUnzipOperator
   :members:
   :undoc-members:
   :show-inheritance:

   