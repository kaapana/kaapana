.. _concepts_workflow_distribution:
.. _concepts_extensions_system:

Distributing Extensions
#######################################

Installing an extension from the :ref:`Extensions page<extensions>` is a single click.
Getting a workflow, task, or application *to* the Extensions page in the first place is a separate step, and it changed as of the 0.7.0 release.
This page is about *why* two distribution paths exist and how they relate; see :ref:`workflow_dev_guide` and :ref:`application_dev_guide` for the actual build/package/upload steps.

Helm Chart Upload (Pre-0.7.0)
========================================

The only distribution mechanism was a Helm chart, uploaded to the platform (or shipped preinstalled) as a ``.tgz`` and installed with Helm.
That mechanism is simple and still handles most extensions in Kaapana today.
A chart reaches the platform through one of three build paths -- see :ref:`workflow_dev_guide` for the steps of each:

* **Local build and manual upload**, the default path for a workflow still under active development.
* **In-platform build via the EDK**, the **Extension Development Kit**, when the platform is the only environment available.
* **Air-gapped transfer**, for platforms without direct registry access.

Extension Manager (0.7.0+)
=====================================================

0.7.0 added the **Extension Manager**: an extension is packaged as an OCI artifact, described by a manifest, and pulled directly from any standard container registry, instead of being built and uploaded by hand.

Extension Manager currently supports only ``workflow-v1`` content type; with helm charts, application and task extensions coming soon.
See :ref:`concepts_architecture` for the service itself, and the Extension Manager UI for registering OCI registries and installing or uninstalling extensions independently of the existing Extensions page.




