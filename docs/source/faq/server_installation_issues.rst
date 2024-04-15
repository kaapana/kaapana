.. _server_installation_issues:

Server Installation Issues
***************************

**Script terminated by SIGINT (Almalinux)**

| Red Hat Linux, and Almalinux have specific issues where microk8s command executed inside of a bash script are killed with SIGINT with exit code 143 as mentioned `here <https://github.com/canonical/microk8s/issues/3386>`_.
| The script exits with error message `Terminated`.

Potential fixes:

1. Add -E to sudo during server_installation script.sh.

.. code-block:: bash

    sudo -E ./server_installation.sh

2. If installation script was terminated after installing microk8s, but before configuration, then before re-run either uninstall or script modification as following is necessary:

.. code-block:: bash

    # if microk8s status > /dev/null
    if false

3. Try adding ``sleep 60`` command in the script directly after ``snap install microk8s`` and ``microk8s start`` commands