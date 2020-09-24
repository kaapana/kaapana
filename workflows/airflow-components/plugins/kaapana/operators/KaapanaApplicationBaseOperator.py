from datetime import timedelta, datetime
import os
import json
from kaapana.kubetools import ingress_launcher, service_launcher
from kaapana.kubetools.service import Service
from kaapana.kubetools.ingress import Ingress
from kaapana.kubetools.delete_apps import delete_apps_by_run_id
from kubernetes.client.rest import ApiException
from airflow.exceptions import AirflowException

from kaapana.operators.KaapanaBaseOperator import KaapanaBaseOperator


class KaapanaApplicationBaseOperator(KaapanaBaseOperator):
       
    def execute(self, context):

        self.set_context_variables(context)

        if (self.service):
            service = Service(
                name=self.kube_name,
                namespace=self.namespace,
                port=self.port,
                labels=self.labels,
                selector=self.labels
            )

            try:
                launcher = service_launcher.ServiceLauncher(
                    extract_xcom=self.xcom_push)
                launcher.run_service(
                    service,
                    startup_timeout=self.startup_timeout_seconds,
                    get_logs=self.get_logs)

            except AirflowException as ex:
                raise AirflowException(
                    'Service Launching failed: {error}'.format(error=ex))

        if (self.ingress):
            ingress = Ingress(
                name=self.kube_name,
                annotations=self.annotations,
                path=self.ingress_path,
                namespace=self.namespace,
                labels=self.labels,
                service_name=service.name,
                service_port=service.service_port)

            try:
                launcher = ingress_launcher.IngressLauncher(
                    extract_xcom=self.xcom_push)
                launcher.run_ingress(
                    ingress,
                    startup_timeout=self.startup_timeout_seconds,
                    get_logs=self.get_logs)

            except AirflowException as ex:
                raise AirflowException(
                    'Ingress Launching failed: {error}'.format(error=ex))
    
        try:
            super().execute(context=context)
        except ApiException as ex:
            # Caching if Pod was delete externally
            if ex.status == 404 and ex.reason == 'Not Found':
                pass
            else:
                delete_apps_by_run_id(context["run_id"], self.namespace, stop_ingresses=True, stop_services=True)
                raise ApiException(
                    'Something seems to be wrong : {ex}'.format(ex=ex)
                )
        except AirflowException as ex:
            if str(ex)[:29] == 'Pod Launching failed: Timeout':
                print('Closing pod due to timeout')
            else:
                delete_apps_by_run_id(context["run_id"], self.namespace, stop_ingresses=True, stop_services=True)
                raise AirflowException(
                    'Pod starting failed: {ex}'.format(ex=ex)
                )


        print('deleting')
        delete_apps_by_run_id(context["run_id"], self.namespace, stop_pods=True, stop_ingresses=True, stop_services=True)

    def post_execute(self, context, result):
        pass

    def __init__(self,
                dag,
                ingress=False,
                service=False,
                port=None,
                ingress_path=None,
                *args, **kwargs
                 ):

        self.ingress = ingress
        self.service = service
        self.port = port
        self.ingress_path = ingress_path

        super().__init__(
            dag=dag,
            *args, **kwargs
            )
