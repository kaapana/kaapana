.. _faq_debug_kubernetes:

How to debug with Kubernetes
****************************

Here are two examples, when you might need to access Kubernetes:

**Case 1: A Service is down**

In case you can't access a resource anymore, most probably a Pod within Kubernetes is down. To check whats causing the pod to fail you go to the Kubernetes-Dashboard. Select at the top a Namespace and then click on Pods. The pod which is down should appear in a red/orange color. Click on the pod. At the top right, you see four buttons. First click on the left one, this will show the logs of the container. In the best case you see here, why your pod is down. To restart the pod you need to simply delete the pod. In case it was not triggered by an Airflow-Dag it should restart automatically (The same steps can be done via the console, see below). In case the component/service crashes again, there might be some deeper error.

**Case 2: Platform is not responding**

When the whole platform does not respond this can have different reasons.

- Pods are down: In order to check if and which pods are down please log in to your server, and check which pods are down executing:

::

    kubectl get pods -A


If not all pods are running, a first try would be to delete the pod manually. It will then be automatically restarted. To delete a pod via the console. You need do copy the "NAME" and remember the NAMESPACE of the pod you want to delete and then execute:
::

    kubectl delete pods -n <THE NAMESPACE> <NAME OF THE POD>

If all pods are running, most probably there are network errors. This is usually caused by configuring a wrong server domain name during the deployment of the platform.
