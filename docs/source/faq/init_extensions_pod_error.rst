.. _init_extensions_pod_error:

Pod `init-extensions` fails with Error status
*********************************************

If :code:`init-extensions` pod has Error status, and the only namespace available in the platform is :code:`admin` (this can be checked via :code:`kubectl get namespaces`), it is likely that the :code:`kaapana-platform-chart` is not uninstalled correctly from the previous deployment.

Usually in the logs of the pod (can be checked via :code:`kubectl logs -n admin <init-extensions-pod-name>`) a message as follows can be seen: :code:`Error: INSTALLATION FAILED: cannot re-use a name that is still in use`. If that is the case:

1. :code:`kaapana-platform-chart` should be listed under uninstalling charts, check via :code:`helm ls -A --uninstalling`
2. If it is listed, delete via :code:`helm uninstall kaapana-platform-chart --no-hooks`
3. Then redeploy the platform with :code:`./deploy_platform.sh --undeploy`, make sure nothing remains under :code:`helm ls -A --uninstalling`, and run :code:`./deploy_platform.sh` again.
