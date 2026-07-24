.. _feature_preview_root:

==============================================
Feature Preview: New way of extending Kaapana
==============================================

This section previews a new, in-development approach to building and packaging Kaapana extensions.
It replaces ad-hoc, Airflow-specific integration with the standardized **Task API**, making :term:`processing-containers<processing-container>` explicit, self-describing, and easier to validate before deployment.
Building on top of the Task API, the new **Workflow API**, centered around the :code:`KaapanaTaskOperator`, lets you wire processing-containers into Airflow DAGs without writing a custom operator for every container, reducing boilerplate and keeping DAGs consistent across extensions.
Once built, extensions can be distributed and managed through the new **Extension Manager Service**, which lets users discover, install, and uninstall extensions from OCI registries directly from the Kaapana UI, removing the need for manual Helm chart handling.
The result is a simpler development loop: extensions are easier to write, package, and manage independently of the internals of the Kaapana platform, while remaining fully interoperable with it.

.. warning::

    This is a preview of upcoming functionality. APIs and workflows described here may still change before final release.

.. toctree::
    :maxdepth: 2
    :hidden:

    preview/processing_container_dev_guide
    preview/workflow_development
    preview/extension_packaging
    preview/extension_manager
    Hands On Extension Development: Short Walkthrough <preview/hands_on_extension_development_geometric_heads>


