.. _build:

Build Kaapana
*************

It is important to note that the building of Kaapana (including the cloning of the repository etc.) is completely separated from the actual installation / deployment of the platform.
Building the repository, which is described in this chapter, refers to the creation of the required containers and Helm Charts needed for an installation.
The results of this build (containers and charts) are usually pushed into a registry and downloaded from there for the installation on the actual deployment server (where the platform will be running).

.. important::

  | **1) Do you really need to build the project?**
  | Only build the project if you don't have access to an existing registry containing the Kaapana binaries or if you want to setup your own infrastructure. Registry access can be requested from the DKFZ Kaapana Team via `Slack <https://kaapana.slack.com/archives/C018MPL9404>`_.
  |
  | **2) You don't need to build the repository on the deployment server!**
  | A typical misconception we often hear is that you need to clone the repository on the deployment server and build it there. That is not the case! The repository can be built on a completely different machine and the results then made available via a registry. Practically, it is even recommended to separate the repository and the deployment server. Of course it is possible to build the repository on the deployment server (and there is also the possibility to work completely without a registry) - but this should be done in rather rare cases.
  |

Build Requirements
------------------
Perform these steps on the build machine. The recommended build system is Ubuntu 24.04 (x64).
Kaapana can only be built and run on x64 systems.
Building on other operating systems or architectures has not been tested and may lead to unexpected issues, for which no official support is provided.

.. important::

  | **Disk space needed:**
  | For the complete build of the project ~90GB (~110GB including build cache) of container images will be stored at :code:`/var/snap/docker/common/var-lib-docker`.
  | When creating offline installation tarball, ~80GB additional disk space is needed.

Before you get started you should be familiar with the basic concepts and components of Kaapana (see :ref:`What is Kaapana?<about_kaapana>`).
You should also have the following packages installed on your build-system.

#. Dependencies

   .. tabs::

      .. tab:: Ubuntu

         | :code:`sudo apt update && sudo apt install -y nano curl git python3 python3-pip`

      .. tab:: AlmaLinux

         | :code:`sudo dnf update && sudo dnf install -y nano curl git python3 python3-pip`


#. Clone the repository:

   | :code:`git clone -b master https://github.com/kaapana/kaapana.git`

#. Install the build CLI (provides the ``kaapana-build`` command)

   :code:`python3 -m pip install -e kaapana/build_cli`

   .. tip::

      | **Use a virtual environment for installing Python dependencies.**
      | This is a recommended best practice.
      |
      | On Ubuntu 24.04 and similar distributions, due to changes in Python packaging (see `PEP 668 <https://peps.python.org/pep-0668/>`_), installing packages with :code:`pip` outside of a virtual environment may result in errors or warnings.
      |
      | To avoid issues, create and activate a virtual environment **before** running the requirements installation:

      .. tabs::

         .. tab:: venv

            **Recommended for beginners!**

            **Creation step** (only needed once):

            .. code-block:: bash

               # Install the 'venv' package if not already installed
               sudo apt install -y python3-venv

               # Create the virtual environment (only needed once)
               python3 -m venv kaapana/.venv

            **Activation step** (needed each time you use the Python code):

            .. code-block:: bash

               # Activate the virtual environment
               source kaapana/.venv/bin/activate

            Then install the Python requirements.

         .. tab:: pipenv


            **Installation step** (only needed once):

            .. code-block:: bash

               # Install pipenv
               pip install pipenv

               # Create and activate the environment (only needed once)
               pipenv install

            **Activation step** (needed each time you use the Python code):

            .. code-block:: bash

               # Activate the environment
               pipenv shell

            Then install the Python requirements.

         .. tab:: poetry

            **Installation step** (only needed once):

            .. code-block:: bash

               # Install Poetry
               pip install poetry

               # Create and activate the environment (only needed once)
               poetry install

            **Activation step** (needed each time you use the Python code):

            .. code-block:: bash

               # Activate the environment
               poetry shell

            Then install the Python requirements.

         .. tab:: conda

            | **Licensing Notice**: Anaconda has licensing restrictions for commercial use. For details, refer to the `Anaconda Terms of Service <https://www.anaconda.com/terms-of-service>`_.
            |
            | Conda can be installed in various ways, and it’s important to research the best option for your needs to ensure compliance with the relevant licensing terms.
            |
            | If you have Conda installed, you can create and activate a Conda environment and then proceed to install the Python requirements.

            **Creation step** (only needed once):

            .. code-block:: bash

               # Create a Conda environment (only needed once)
               conda create -n kaapana python=3.x

            **Activation step** (needed each time you use the Python code):

            .. code-block:: bash

               # Activate the Conda environment
               conda activate kaapana

            Then install the Python requirements

#. Snap

   .. tabs::

      .. tab:: Ubuntu

         | Check if snap is already installed: :code:`snap help --all`
         | If **not** run the following commands:
         | :code:`sudo apt install -y snapd`
         | A **reboot** is needed afterwards!

      .. tab:: AlmaLinux

         | Check if snap is already installed: :code:`snap help --all`
         | If **not** run the following commands:
         | :code:`sudo dnf install -y epel-release && sudo dnf install -y snapd`
         | A **reboot** is needed afterwards!

#. Docker

   Install Docker following the `official Docker installation guide <https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository>`_.

   .. attention::
      Installing Docker via ``snap`` is not recommended -- it fails to work correctly on many systems. Use the official installation method linked above.

#. In order to execute docker commands as non-root user you need to execute the following steps:

   | :code:`sudo groupadd docker`
   | :code:`sudo usermod -aG docker $USER`
   | For more information visit the `Docker docs <https://docs.docker.com/engine/install/linux-postinstall/>`_

#. Helm

   :code:`sudo snap install helm --classic --channel=latest/stable`

#. kubeconform

   | :code:`curl -fsSL https://github.com/yannh/kubeconform/releases/download/v0.7.0/kubeconform-linux-amd64.tar.gz | tar -xz -C ~/.local/bin kubeconform`
   | -> validates the Helm charts on every build; skip with :code:`--no-linting`

#. Reboot

   :code:`sudo reboot`

#. Test Docker

   | :code:`docker run hello-world`
   | -> this should work now without root privileges


Start Build
------------

Choose the tab that matches how you build: **Remote Registry** for a normal build pushed to your own registry, **Local Registry** for a disposable local registry for one-off testing, and **Tarball** for producing offline installation artifacts. For installing onto the target server afterwards -- online, registry-only, or fully air-gapped -- see :ref:`faq_offline_installation` for the registry-only and offline paths specifically.

.. tabs::

   .. tab:: Build With Remote Registry

      We recommend building the project using a registry. If you do not have access to an established registry, we recommend using `Gitlab <https://gitlab.com>`_, which provides a cost-free option to use a private container registry.

      .. code-block:: python

         kaapana-build --default-registry <registry-url> --registry-username <registry-username> --registry-password <registry-password>

      .. note::
         1. If the username and password are not working, you may need to use an **access token** instead.
         2. Ensure that the **username/access token does not contain spaces**.

   .. tab:: Build With Local Registry

      | Not recommended.
      | If a private registry is not available, it is possible to setup a local registry.
      | This may be helpful for one-time show-casing, testing, developing, or if there are any issues with connection to the remote registry.
      | This solution is only persistent while the docker container containing the registry is running. The registry uses plain HTTP and is meant for a single server, on which you build and deploy Kaapana.
      | For building with a local registry, you need to set up a local Docker registry with basic authentication with following steps:

      1. Create credentials (replace **<registry user>** and **<registry password>**):

         .. code-block:: bash

            mkdir auth
            docker run --entrypoint htpasswd httpd:2.4.58 -Bbn <registry user> <registry password> > auth/htpasswd


      2. Start the Docker registry with basic authentication on the host network:

         .. code-block:: bash

            docker run -d --network host --restart unless-stopped --name registry -v "$(pwd)"/auth:/auth -e "REGISTRY_AUTH=htpasswd" -e "REGISTRY_AUTH_HTPASSWD_REALM=Registry Realm" -e REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd registry:2.8.3

         | With :code:`--network host` the registry listens on port 5000 of the server and does not use the Docker bridge network. Do not add :code:`-p`, because Docker ignores it in this mode.
         | The registry should be reachable from inside the cluster, because the Extension Manager reads the default extension repository from it. On a server with MicroK8s, pods could not reach a registry that Docker published with :code:`-p 5000:5000` on the IP address of the server.


      3. Allow the container engine to use the registry without TLS. Replace **<node-ip>** by the IP address of the server, which the cluster can reach. Add :code:`<node-ip>:5000` to the insecure registries of the container engine and restart the engine. The place of this setting depends on the installation. See :ref:`plain_http_registry`.


      4. Run the build against the registry:

         .. code-block:: python

            kaapana-build --registry-username <registry user> --registry-password <registry password> --default-registry "<node-ip>:5000" --plain-http

         .. important::

            | Do not use :code:`localhost:5000` as :code:`--default-registry` if you deploy on the same server. The registry name is part of every image name. Inside a pod, :code:`localhost` is the pod itself, so the Extension Manager cannot reach the default extension repository. See :ref:`extension_manager`.
            | For the deployment, the container runtime of the cluster also needs a setting for plain HTTP registries. See :ref:`the installation <deployment>`.


   .. tab:: Build Tarball

      | Not recommended.
      | In case platfrom should be deployed in the machine without internet access (i.e. offline),
      | installation files, containers and helm charts need to be pre-build on the server
      | with internet access and copied on the server, where requirements can be installed and platfrom deployed.
      | This configuration creates an image tarball and offline microk8s installer

      .. code-block:: python

         kaapana-build --build-only --create-offline-installation --default-registry offline

      | Installer will be available in ``kaapana/build/microk8s-offline-installer``
      | Tarball will be available in ``kaapana/build/kaapana-admin-chart/kaapana-admin-chart-<version>-images.tar``

      | To bundle AI model weights into the container images themselves, so they are already present on the offline machine, add the ``--include-model-weights`` flag (or set ``INCLUDE_MODEL_WEIGHTS=true`` in your ``.env``) to the command above.


This takes usually (depending on your hardware) around 1h.
You can find the build-logs and results at :code:`./kaapana/build`

.. hint::
   You can also set parameters as environment variables or store them in a :code:`.env` file in your working directory.
   For a full list of all options execute :code:`kaapana-build --help`


.. _plain_http_registry:

Using a Plain HTTP Registry
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Read this section if your registry uses plain HTTP instead of HTTPS, for example the registry from the tab **Build With Local Registry**.
Docker, BuildKit and Helm use HTTPS by default, so the build cannot connect to such a registry without the two steps below.
The steps cover only the build.
For the deployment, the cluster needs its own setting, see :ref:`the installation <deployment>`.

In the examples, replace :code:`<registry>` by the host and port of your registry, without a path, for example :code:`10.0.0.5:5000`.

.. note::
   Docker and BuildKit accept plain HTTP for :code:`localhost` and :code:`127.0.0.1` without any setting, so such a registry does not need step 1.
   However, do not use such a registry if you want to deploy Kaapana from it.
   The Extension Manager reads the default extension repository from the registry, and inside a pod :code:`localhost` is the pod itself.
   See :ref:`extension_manager`.

#. Allow the registry in the container engine.

   :code:`kaapana-build` uses the container engine to log in to the registry and to push and pull images.
   The build tool cannot change this setting, because the change needs root rights and a restart of the engine.
   If the setting is missing, the login fails with ``http: server gave HTTP response to HTTPS client``.

   The file and the restart command depend on how the container engine is installed.
   If you installed Docker as described in the build requirements above, use the row **Docker Engine**.
   Ubuntu can also install Docker as a snap. Run :code:`snap list docker` to find out if this is the case.

   .. list-table::
      :header-rows: 1
      :widths: 25 45 30

      * - Installation
        - File
        - Restart command
      * - Docker Engine (apt, convenience script)
        - :code:`/etc/docker/daemon.json`
        - :code:`sudo systemctl restart docker`
      * - Docker as snap
        - :code:`/var/snap/docker/current/config/daemon.json`
        - :code:`sudo snap restart docker`
      * - Docker rootless
        - :code:`~/.config/docker/daemon.json`
        - :code:`systemctl --user restart docker`
      * - Docker Desktop
        - **Settings** > **Docker Engine**
        - **Apply & restart**
      * - Podman (:code:`--container-engine podman`)
        - :code:`/etc/containers/registries.conf`
        - Not needed

   For Docker, add the registry to the list :code:`insecure-registries`.
   If the file does not exist, create it with the following content.
   If it exists, keep its content and only add the list or the entry:

   .. code-block:: json

      {
        "insecure-registries": ["<registry>"]
      }

   For Podman, add the following block to :code:`registries.conf`:

   .. code-block:: toml

      [[registry]]
      location = "<registry>"
      insecure = true

   .. warning::
      Restarting Docker stops all running containers, unless :code:`live-restore` is enabled in :code:`daemon.json`.
      Containers with a restart policy start again, for example the registry from the tab **Build With Local Registry**.
      Containers without a restart policy stay stopped, and you must start them again yourself.

   Restart the container engine with the command from the table.
   Then check that Docker lists the registry. The output must contain :code:`<registry>`:

   .. code-block:: bash

      docker info | sed -n '/Insecure Registries/,/Live Restore/p'

#. Add the flag :code:`--plain-http` to the build command, for example:

   .. code-block:: bash

      kaapana-build --default-registry <registry> --registry-username <registry-username> --registry-password <registry-password> --plain-http

   The setting from step 1 does not apply to Helm, which pushes the charts.
   It also does not apply to the BuildKit builder, which builds and pushes the images if you use :code:`--cache-from` or :code:`--cache-to`.
   The flag :code:`--plain-http` sets up both.
   If a builder from an earlier run exists, the build removes it and creates it again, because the setting of an existing builder cannot be changed.


The next step will explain how to install the Kubernetes cluster via the :code:`kaapanactl.sh` script.
