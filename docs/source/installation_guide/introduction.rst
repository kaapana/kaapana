Introduction
************

This manual serves as a resource for getting started with Kaapana. Kaapana is a highly customizable platform toolkit designed to facilitate the creation of a platform tailored to the specific requirements of your project. 
It provides a core system along with several pre-built functionalities, such as image curation, workflow management, and training and inference capabilities for medical imaging models (specifically nnUnet). 

If you want to deploy the platform as it is, you can request access to our container registry through `Slack <https://kaapana.slack.com/archives/C018MPL9404>`_. While the platform can be adjusted manually with additional extensions, custom web applications, and manually defined workflows, 
for more extensive development, we recommend following the :ref:`build process<build>` to populate a custom registry with your own images.

Refer to the flowchart below for deciding which section of the installation guide is relevant for your use case.

.. mermaid::

    flowchart TB
        a1["Build Kaapana"]-->a2["Push charts and containers to a remote registry or store locally in a tarball"]-->a3["Server Installation"]-->a4["Platform Deployment"]
