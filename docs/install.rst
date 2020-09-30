Generic Kaapana system installation
===============================

This document describes the setup of a system for the DKTK Joint Imaging
Platform. It is assumed that an independent system is desired for the
platform.

All required files can be found in the D:cipher repository:

::

    kaapana/joint_imaging_platform/server_installation/gerneric_centos_installation/

Requirements
------------

-  OS is CentOs
-  proxy configured (If necessary)
-  Internet access
-  Root privileges

Steps of the procedure
----------------------

1. Installation of the dependencies (centos\_installer.sh)
2. Deployment of the Components

1. Installation of the dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here all software dependencies will be installed.

**important**:

The following steps will be executed in the script:

-  **firewalld will be disabled**
-  **iptables will be reconfigured**
-  swap will be turned off (required by Kubernetes)
-  selinux will be set to permissive (required by Docker)
-  Docker-CE will be installed
-  All Kubernetes tools will be installed (v.1.11)

If GPU support is desired (optional): - NVIDIA drivers will be installed
- Nvidia-Docker2 will be installed

The rest is configuration for all the components. After installation,
the following ports will be open on the server: - Port 80 -> http
communication - Port 443 -> https communication - Port 8080 ->
authentication server frontend - Port 22 -> SSH - Port 6443 ->
Kubernetes API - Port 11112 -> DICOM receiver port

**Copy install script** To proceed, copy the script
**centos\_installer.sh** to the server. There are several ways to do
this: **scp**

::

    scp ./centos_installer.sh <server-user>@<server-ip>:/<target-dir>

**Or** via any **text editor** SSH into your machine and launch a shell
text editor. Copy and paste the script from your machine into the
console. eg:

::

    nano  centos_installer.sh

**Start the script**

Make the file executable (@server):

::

    chmod +x ./centos_installer.sh

start the script (@server)

::

    sudo ./centos_installer.sh

The execution of the script should be self-explanatory. You will be
asked a couple of questions during the process.

**GPU support:** Right now only NVIDIA gpus are supported. If you have
such a card in your system you should enable the support.

**Meanwhile** This will take some time (~30 min). You can already
install kubectl on your machine, which is described in the *3.
Deployment of the Components* section.

**End of the script** You should now be presented with a certificate.
Read the instructions in the output. **--> save the presented
certificate at the end of the process** 1. Copy the text between the
dashes 2. Create a file at ~/.kube/config on your machine 3. Paste the
text certificate into the config file

3. Deployment of the Components
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This part is about the deployment of the platform components themself.
#### Installation of kubectl You can do this directly on the server or
remote from your machine. If you want to do this from your machine
(recommended for future work), you need to install the **kubectl**
application on your system. (This application and is already installed
and configured on the server.) Follow this instructions: `How to install
Kubectl <https://kubernetes.io/docs/tasks/tools/install-kubectl/#install-kubectl>`__

To enable the communication between kubectl and the Kubernetes API
server, you need to setup the **previously presented certificate** from
step 2. To do this you need to create a config file at:

::

    nano ~/.kube/config

Paste the certificate from above in the file. You should now be able to
communicate with the Kubernetes instance. check:

::

    kubectl get pods --all-namespaces

You should now see a list of some Kubernetes resources.

**If not** check the IP-address at the beginning of your config file.

::

    server: <SERVER-IP-ADDRESS>

This should match the IP you are using for SSH. #### untaint
master-server kubectl taint nodes --all node-role.kubernetes.io/master-
#### Deployment The required files can be found in the D:cipher
repository:

::

    /kaapana/platform_deployment

Script file:

::

    deploy_platform.sh

Make the file executable (if not already):

::

    chmod +x ./deploy_platform.sh

start the script:

::

    ./deploy_platform.sh

The execution of the script should be self-explanatory. You will be
asked a couple of questions during the process.

**TARGET DIR** There will be files generated for your configuration. You
should specify a location on your machine, where these files can be
placed.

**Mounting points** This are the locations, where all the stateful data
is saved at from the platform. If you run this script on the default kaapana
server, you can keep the defaults. Otherwise, you should make some
adjustments.

The platform differentiates between fast storage (like SSD) and slow
storage (like HDD). You will be asked for both mounting points during
the process. You should enter a path to the corresponding location on
your server where the drives are mounted.

*If you don't have seperate drive types, you can use the same directory
for both.*

After the deployments were sent to the server, you have to wait for the
platform to come alive. This could take some time, because all the
components have to be downloaded to the server. You can check the
process by using:

::

    kubectl get pods --all-namespaces

You will get a list of all components and the state they are currently
in.

::

                 READY                      STATUS
        num_running/num_expected      Should be Running

You should wait till all components are either running or completed. If
there are some issues with this process you should take a look
@troubleshooting.

When everything went fine, you can visit your server at:

::

    https://<server-ip_address>/
    or
    https://<domain>/

And should be welcomed by a login-screen.
