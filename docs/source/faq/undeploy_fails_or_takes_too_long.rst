.. _faq_undeploy_fails_or_takes_too_long:

Undeployment fails or takes too long
************************************

If some Kubernetes resources from the Kaapana deployment are **not in a** ``Running`` **or** ``Completed`` **state**, undeployment might hang or fail.

Use Deployment Script Flags
##############################

Kaapana provides deployment script flags to help resolve common undeployment issues:

- ``--no-hooks``
  Purges all Kubernetes deployments, jobs, and Helm charts **without running pre/post delete hooks**.
  Use this if undeployment **fails** or **runs indefinitely**.

- ``--nuke-pods``
  Force-deletes all pods within Kaapana-related namespaces.
  Useful if stuck pods are blocking removal.

Run the deployment script with one or both of these flags:

.. code-block:: bash

   ./kaapanactl.sh deploy --no-hooks
   ./kaapanactl.sh deploy --nuke-pods

Manual Undeployment (Advanced)
###############################

If the above options don’t resolve the issue, you can manually undeploy Kaapana.
> ⚠️ **Warning:** Only perform these steps if you are familiar with Kubernetes and Helm.

Step 1 – Remove Helm Releases
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Check for existing releases:

.. code-block:: bash

   helm ls -n admin
   helm ls -n admin --uninstalling
   helm ls -n default
   helm ls -n default --uninstalling

Uninstall any Kaapana-related charts (e.g., platform-chart, admin-chart, project-charts):

.. code-block:: bash

   helm uninstall -n <namespace> <chart-name> --no-hooks

Ensure that no Kaapana Helm releases remain.

Step 2 – Delete Namespaces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

List current namespaces:

.. code-block:: bash

   kubectl get namespaces

Remove any Kaapana-specific namespaces, such as:

- ``services``
- ``admin``
- ``project-<name>``

Delete each one manually:

.. code-block:: bash

   kubectl delete namespace <namespace>

Step 3 – Clean Up Persistent Volumes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Check for remaining persistent volumes:

.. code-block:: bash

   kubectl get pv

If needed, delete all persistent volumes:

.. code-block:: bash

   kubectl delete pv --all