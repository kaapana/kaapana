# First install kubernetes with pip (code-server from the extensions running on the server)
# python3 -m pip install kubernetes

from kubernetes import config, client
from kubernetes.client import Configuration
from six import PY2
import time

def _load_kube_config(in_cluster, cluster_context, config_file):
    if in_cluster:
        config.load_incluster_config()
    else:
        config.load_kube_config(config_file=config_file,
                                context=cluster_context)
    if PY2:
        # For connect_get_namespaced_pod_exec
        configuration = Configuration()
        configuration.assert_hostname = False
        Configuration.set_default(configuration)
    return client.CoreV1Api(), client.BatchV1Api(), client.NetworkingV1Api()


_client, _batch_client, _extensions_client = _load_kube_config('in_cluster', cluster_context=None, config_file=None)
namespace="default"

try:
    pods = _client.list_namespaced_pod(namespace=namespace, pretty=True).items
    pods_list = [pod.metadata.name for pod in pods]    

    i=0
    for pod in pods:
        print("Pod {}: {}".format(i,pod.metadata.name))
        i+=1

except Exception as e:
    print("Kube-API exception!")
    print(e)