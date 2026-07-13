.. _develop_guide:

Extending Kaapana
#################

Kaapana is designed to be extended by its users. Extensions can take the form of
algorithms packaged as :doc:`OCI containers <development_guide/preview/processing_container_dev_guide>`,
data-processing pipelines as :doc:`workflows <development_guide/preview/workflow_development>`, or
server applications with backend and frontend services.

For deployments older than version 0.7.0, refer to the
:doc:`Legacy Development Guide <development_guide/legacy_dev_guide_root>`,
which covers workflow and application extension development for those releases.

Since version 0.7.0 you should consider to use the :doc:`New way of extending Kaapana <development_guide/feature_preview_root>`,
which covers workflow, task and extension development with new and cleaner APIs.

.. toctree::
    :maxdepth: 2
    :hidden:

    
    development_guide/legacy_dev_guide_root
    development_guide/feature_preview_root
    development_guide/legacy_workflow_migration

