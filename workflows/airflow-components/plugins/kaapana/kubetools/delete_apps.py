import shutil
import os
import re
from kaapana.kubetools.pod_finder import PodFinder
from kaapana.kubetools.pod_stopper import PodStopper
from kaapana.kubetools.service_finder import ServiceFinder
from kaapana.kubetools.service_stopper import ServiceStopper
from kaapana.kubetools.ingress_finder import IngressFinder
from kaapana.kubetools.ingress_stopper import IngressStopper
from kaapana.kubetools.pod_finder import PodFinder
from kaapana.kubetools.pod_stopper import PodStopper

from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

def delete_apps_by_run_id(run_id, namespace=None, stop_ingresses=False, stop_services=False, stop_pods=False):

    if stop_ingresses:
        ingress_finder = IngressFinder()
        ingress_stopper = IngressStopper()
        ingresses = ingress_finder.find_ingress(namespace).items
        for ingress in ingresses:
            if ingress.metadata.labels is not None:
                if 'run_id' in ingress.metadata.labels:
                    if run_id == ingress.metadata.labels['run_id']:
                        print("deleting ingress", ingress)
                        ingress.kind = "Ingress"
                        ingress_stopper.stop_ingress(ingress)

    if stop_services:
        service_finder = ServiceFinder()
        service_stopper = ServiceStopper()
        services = service_finder.find_service(namespace).items
        for service in services:
            if service.metadata.labels is not None:
                if 'run_id' in service.metadata.labels:
                    if run_id == service.metadata.labels['run_id']:
                        print("deleting service", service)
                        service.kind = "Service"
                        service_stopper.stop_service(service)

    if stop_pods:
        pod_finder = PodFinder()
        pod_stopper = PodStopper()
        pods = pod_finder.find_pod(namespace).items
        for pod in pods:
            if pod.metadata.labels is not None:
                if 'run_id' in pod.metadata.labels:
                    if run_id == pod.metadata.labels['run_id']:
                        print("deleting pod", pod)
                        pod.kind = "Pod"
                        pod_stopper.stop_pod(pod)              
