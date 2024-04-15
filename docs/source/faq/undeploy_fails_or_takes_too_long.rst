Undeployment fails or takes too long
************************************
| If some Kubernetes resources of the Kaapana deployment are not in a :code:`Running` or :code:`Completed` state, there might be some issues with undeployment.

| First thing to try for this issue is to use some of the flags in the deploy script that can help with incomplete undeployments, i.e. :code:`./deploy_platform.sh --no-hooks` or :code:`./deploy_platform.sh --nuke-pods`

| :code:`--no-hooks` will purge all kubernetes deployments and jobs as well as all helm charts. Use this if the undeployment fails or runs forever.
| :code:`--nuke-pods` will force-delete all pods of the Kaapana deployment namespaces.

| If none of the flags solve the issue, you can try and manually undeploy the platform. Note that running these commands is NOT recommended for users that are not familiar with how to directly interact with Kubernetes and Helm.

| **1.** Check if there are any platform deployments are listed under :code:`helm ls -A` or :code:`helm ls -A --uninstalling`. If there are, remove with :code:`helm uninstall <chart-name> --no-hooks`. It is important that no platform-chart or admin-chart remains after undeployment.
| **2.** Next step is to look at the namespaces via :code:`kubectl get namespaces` and check whether any of the following are listed there: :code:`extensions, jobs, services, admin`. If there are, you can remove all the resources under that namespace via :code:`kubectl delete namespace <namespace>`.
| **3.** Last step is to check if there are any remaining persistent volumes, via :code:`kubectl get pv`. You can remove them all by running :code:`kubectl delete pv --all`
