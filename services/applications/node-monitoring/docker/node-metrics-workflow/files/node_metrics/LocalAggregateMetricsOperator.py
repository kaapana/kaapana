from datetime import timedelta
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
import requests

class LocalAggregateMetricsOperator(KaapanaPythonBaseOperator):
    def start(self, ds, **kwargs):
        try:
            r = requests.get(
                self.metrics_endpoint, timeout=self.timeout, verify=self.verify_ssl
            )
        except requests.exceptions.Timeout:
            pass
        except requests.exceptions.TooManyRedirects:
            pass
        except requests.exceptions.RequestException as e:
            pass

    def __init__(
        self, dag, metrics_endpoint, component_id, timeout=5, verify_ssl=False, **kwargs
    ):
        self.metrics_endpoint = metrics_endpoint
        self.component_id = component_id
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        super().__init__(
            dag=dag,
            name="get-metrics",
            parallel_id=component_id,
            python_callable=self.start,
            **kwargs
        )
