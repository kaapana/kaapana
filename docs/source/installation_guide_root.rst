.. _installation_guide:

Installation Guide
##################

This manual serves as a resource for deploying Kaapana on a server.

If you want to deploy the platform as it is, you can request access to our container registry through `Slack <https://kaapana.slack.com/archives/C018MPL9404>`_. 
While the platform can be adjusted manually with additional extensions, custom web applications, and manually defined workflows, 
for more extensive development, we recommend following the :ref:`build process<build>` to populate a custom registry with your own images.

Getting Kaapana deployed on your server consists of three streps:

#. **Building the platform**: This includes the platform itself, as well as all required containers and helm charts.
#. **Installing the kubernetes cluster and depencencies**: This step involves setting up the Kubernetes cluster and installing all necessary dependencies.
#. **Deploying Kaapana**: Finally, you deploy all helm charts and containers to the Kubernetes cluster.

The following flowchart should illustrate which steps you have to take to deploy a Kaapana platform on your server.
We assume that you have a server at hand, that satisfies the :ref:`hardware and network requirements<requirements>`.


.. mermaid::

    %%{init: {'themeVariables': {
        'fontFamily': 'Arial, sans-serif',
        'fontSize': '16px',
        'nodeTextColor': '#000000',
        'primaryColor': '#f9f9f9',
        'primaryBorderColor': '#333',
        'lineColor': '#333',
    }}}%%

    graph TD
        A[Does the server have<br/>internet access]
        
        A -->|No| E[<b>Build Kaapana</b> and<br/>create tarballs for<br/>all requirements]
        E --> F[<b>Install the Kubernetes cluster</b><br/> from the tarballs.]
        F --> G[<b>Deploy Kaapana</b><br/>from the tarballs.]


        A --> |Yes| D[Do you want to<br/>customize Kaapana?]
        D --> |No| K[Ask our team for an<br/>access token to our<br/>container registry.]
        K --> H[<b>Install the Kuberntes cluster</b>.]
        H --> I[<b>Deploy Kaapana</b> from<br/>the container registry.]
        
        
        D --> |Yes| B[Do you have read/write access <br/>to a container registry<br/>such as GitLab?]
        B -->|Yes| C[<b>Build Kaapana</b> and<br/>push the containers<br/>to the registry.]
        C --> H
        
        B --> |No| L[Deploy a local<br/>registry on the server]
        L --> C



.. toctree::
    :maxdepth: 2

    installation_guide/requirements
    installation_guide/build
    installation_guide/server_installation
    installation_guide/deployment
    installation_guide/advanced_build_system