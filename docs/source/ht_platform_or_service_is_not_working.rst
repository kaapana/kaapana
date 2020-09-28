.. _platform_is_not_working_doc:

Components is not working or platform is not responding
========================================================

Case 1: Pod (component) is down
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In case a pod is down first you should check why. For this you go to the Kubernetes-Dashboard. Select on the left your Namespace and then click on Pods. The pod which 
is down should appear in a red/orange color. Click ont he pod. Add the top right you see four buttons. First click on the left one, this will show the logs of the container.
In the best case you see here, why your pod is down. To restart the pod you need to simply delete the pod. In case it was not triggered by an Airflow-Dag it should restart automatically
(The same steps can be down via the console, see below).
In case the component/service crashes again, please contact the JIP-Team.

Case 2: Platform is not responding
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When your platform does not respond this can have different reasons.
- Pods are down: In order to check if and which services are down please log in to your server, where you can check if pods are down with:

::

    kubectl get pods --all-namespaces

If all pods are running, most probably there are network errors. If not, a first try would be to delete the pod manually. It will then be
automatically restarted. To delete a pod via the console. You need do copy the "NAME" and remember the NAMESPACE of the pod you want to delete and then execute:
::

    kubectl delete pods -n <THE NAMESPACE> <NAME OF THE POD>

- Network errors: In case of network erros, there seems to be an error within your local network. E.g. your server domain might not work. In this case you could for
example reinstall the platform by first deleting the jip_config.json file and then entering your IP-Address also when the script ask for the server_domain. If you are
sure that in your local network everything is correctly set, please contact the JIP-Team. 
