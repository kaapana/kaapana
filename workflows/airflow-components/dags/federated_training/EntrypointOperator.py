import os
import time

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator, rest_self_udpate
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class EntrypointOperator(KaapanaPythonBaseOperator):

    @rest_self_udpate
    def start(self, ds, ti, **kwargs):
        """
        Determining which path to go through the DAG (using info given by received API call).
        This function sets successor-value which is used by following branching-operator.
        """

        successor = None
        print('#'*50, 'Model was trained for {}/{} federated rounds!'.format(self.fed_round, self.fed_rounds_total))

        if self.init_model:
            print('Model will be initialized - first iteration!')
            successor = 'init-model'
        
        else:
            # compare current fed_round with total number of fed_rounds to train
            if self.fed_round == self.fed_rounds_total:
                print('Training is done - now save final model to Minio!')
                successor = 'final-model-to-minio'
            else:
                print('Continue with federated Training round!')
                successor = 'model-to-minio'

        # push information for branching operator
        print('Successor:', successor)
        ti.xcom_push(key='successor', value=successor)


    def __init__(
        self,
        dag,
        init_model=None,
        fed_round=None,
        fed_rounds_total=None,
        *args,**kwargs):

        self.init_model = init_model
        self.fed_rounds_total = fed_rounds_total
        self.fed_round = fed_round if fed_round is not None else 0

        super().__init__(
            dag,
            name='entrypoint',
            python_callable=self.start,
            *args, **kwargs
        )
