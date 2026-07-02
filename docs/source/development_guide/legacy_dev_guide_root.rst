.. _legacy_dev_guide:

Legacy Development Guide
#########################

.. warning::

    This section shows a legacy way for developing extensions in Kaapana.
    The used APIs are marked for deprecation.

This guide is intended to provide a quick and easy way to get started with developing, deploying and running custom extensions for Kaapana.
 
It consists of three parts. This part gives a brief overview over the technologies and needed preparations for the rest of the guide.
The part :ref:`workflow_dev_guide` focuses on the integration of custom processing workflows into the platform. These can be as simple as collecting metadata from DICOM images or as complex as a full-fledged machine learning pipeline.
This section explains how to write Airflow-DAGs and how to integrate custom workflows as extensions into the Kaapana technology stack.
The last section :ref:`application_dev_guide` provides instructions on deploying a general-purpose web application inside Kaapana.

.. important::
   The reader should be familiar with basic concepts of the Kaapana platform. If you are not, please refer to the :ref:`user_guide` for a general introduction to the concept of the platform and its components.

.. toctree::
    :maxdepth: 2
    :hidden:

    legacy/terminology
    legacy/technologies
    legacy/workflow_dev_guide
    legacy/application_dev_guide
    legacy/workflow_extension_with_custom_registry
    legacy/drag_and_drop_workflow_extension
    legacy/upgrading_extensions_in_kaapana_extension_collection
    legacy/operators
    legacy/services
    legacy/helm_charts
    legacy/best_practices_root





