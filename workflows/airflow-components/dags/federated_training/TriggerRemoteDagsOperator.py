import json
import requests

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator, rest_self_udpate
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class TriggerRemoteDagsOperator(KaapanaPythonBaseOperator):

    @rest_self_udpate
    def start(self, ds, **kwargs):
        """
        Calls the APIs of the participants to start the Training-DAGs there.
        The API call contains all needed information as seen above.
        
        If you need more parameters for your experiment, you can add them here - 
        this will not affect other experiments since they can handle 'unknown'/new
        parameters.
        Make sure you add them in the 'model-training' section of the call.
        """

        assert self.procedure in ['avg', 'seq'], 'You have to provide either "avg" or "seq" as procedure - stopping...'
        
        # only needed for initial dag run (worker not yet given as global value)
        if self.worker is None and self.procedure == 'seq':
            self.worker = self.participants[0]
            print('Set initial worker to {}'.format(self.worker))
        if self.fed_round is None:
            self.fed_round = 0
            print('Set initial fed_round to 0')
        
        # Determine for which worker(s) to wait
        participants = self.participants if self.procedure == 'avg' else [self.worker]

        print('Remote Dag to trigger: {}'.format(self.dag_name))
        
        # API Call
        for participant in participants:
            rest_call = {
                'rest_call': {
                    'global': {
                        'bucket_name': self.bucket_name},
                    'operators': {
                        'model-training': {
                            'host_ip': participant,
                            'n_epochs': self.epochs_on_worker,
                            'use_cuda': self.use_cuda,
                            'batch_size': self.batch_size,
                            'learning_rate': self.learning_rate,
                            'weight_decay': self.weight_decay,
                            'fed_round': self.fed_round,
                            'validation': self.validation,
                            'val_interval': self.val_interval,
                            'seed': self.seed},
                        'minio-action-get-model': {
                            'minio_host': self.scheduler},
                        'model-to-scheduler-minio': {
                            'minio_host': self.scheduler}}}}

            url = 'https://{}/flow/kaapana/api/trigger/{}'.format(participant, self.dag_name)
            r = requests.post(url=url, json=rest_call, verify=False)
            
            print('Triggering Dag on {}'.format(participant), r.json())
            print('API_CALL:')
            print(json.dumps(rest_call, indent=4))


    def __init__(
        self,
        dag,
        dag_name=None,
        worker=None,
        procedure=None,
        participants=None,
        bucket_name=None,
        scheduler=None,
        epochs_on_worker=None,
        batch_size=None,
        learning_rate=None,
        weight_decay=None,
        use_cuda=None,
        fed_round=None,
        validation=None,
        val_interval=None,
        seed=None,
        *args,**kwargs):

        self.dag_name = dag_name
        self.worker = worker
        self.procedure = procedure
        self.participants = participants
        self.bucket_name = bucket_name
        self.scheduler = scheduler

        # model training operator
        self.epochs_on_worker = epochs_on_worker
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.use_cuda = use_cuda
        self.fed_round = fed_round
        self.validation = validation
        self.val_interval = val_interval
        self.seed = seed

        super().__init__(
            dag,
            name='trigger-remote-dags',
            python_callable=self.start,
            *args, **kwargs
        )
