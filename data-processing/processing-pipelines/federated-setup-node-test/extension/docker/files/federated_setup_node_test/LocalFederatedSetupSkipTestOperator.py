# !!! DEPRECATION WARNING: Local Operators are deprecated and will be replaced with operators that run in Kubernetes pods in the next release v0.7.0.
# If you have a custom Local Operator, it should be migrated to a processing container based operator.
from datetime import timedelta

from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalFederatedSetupSkipTestOperator(KaapanaPythonBaseOperator):
    @cache_operator_output
    def start(self, ds, **kwargs):
        conf = kwargs["dag_run"].conf
        print("conf", conf)
        return

    def __init__(self, dag, **kwargs):
        super(LocalFederatedSetupSkipTestOperator, self).__init__(
            dag=dag,
            name="federated-setup-skip-test",
            python_callable=self.start,
            execution_timeout=timedelta(minutes=30),
            **kwargs,
        )
