import os
import glob
import time
import json
import shutil
import requests

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from kaapana.blueprints.kaapana_utils import generate_run_id
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator, rest_self_udpate

from airflow.api.common.experimental.trigger_dag import trigger_dag as trigger


class TriggerMyselfOperator(KaapanaPythonBaseOperator):

    @rest_self_udpate
    def start(self, ds, **kwargs):
        """
        Based on the previous API call, the next DAG-run is started. Information such as federated-round is updated
        accordingly.
        Folders are transferred to new Airflow-Workflow-Directory.
        """

        assert self.procedure in ['avg', 'seq'], 'You have to provide either "avg" or "seq" as procedure - stopping...'

        # only needed for initial dag run (worker not yet given as global value)
        if self.worker is None and self.procedure == 'seq':
            self.worker = self.participants[0]
            print('Set initial worker to {}'.format(self.worker))

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)

        # Transfer model and checkpoints to use them in next dag run
        dag_id = kwargs['dag'].dag_id
        dag_run_id = generate_run_id(dag_id)
        print("New Dag-Run-ID: {}".format(dag_run_id))

        print("Start copying all files from directories: {}".format(self.action_dirs))
        for directory in self.action_dirs:            
            target_dir = os.path.join('data', dag_run_id, directory)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            
            if os.path.exists(run_dir + f'/{directory}'):
                file_list = glob.glob(run_dir + f'/{directory}/*', recursive=True)
                for file in file_list:
                    shutil.copyfile(file, os.path.join(target_dir, os.path.basename(file)))
        
        
        conf_new = kwargs['dag_run'].conf
        
        # Update configuration (API call) for next federated training round
        try:
            current_round = conf_new['rest_call']['global']['fed_round']
            print('Current federated round {}'.format(current_round))
        except KeyError:
            current_round = 0
            print('Initial Dag for this experiment - current federated round is set to 0')
        
        # Sequential procedure
        if self.procedure == 'seq':
            next_worker = self.determine_next_worker(self.participants, current_worker=self.worker)
            next_round = current_round + 1 if next_worker == self.participants[0] else current_round

            conf_new['rest_call']['global']['worker'] = next_worker
            conf_new['rest_call']['global']['fed_round'] = next_round
            conf_new['rest_call']['operators']['entrypoint'] = {'init_model': False}
            print('Completed training iteration on worker: {}'.format(self.worker))
        
        # Averaging procedure
        elif self.procedure == 'avg':
            next_round = current_round + 1
            conf_new['rest_call']['global']['fed_round'] = next_round
            conf_new['rest_call']['operators']['entrypoint'] = {'init_model': False}
            print('Completed federated round: {}'.format(current_round))
        
        # Trigger new dag
        print('API_CALL:')
        print(json.dumps(conf_new, indent=4))
        
        print('Trigger next dag to continue training')
        trigger(dag_id=dag_id, run_id=dag_run_id, conf=conf_new, replace_microseconds=False)


    def determine_next_worker(self, participants, current_worker):
        """Returns next worker based on current_worker"""
        position_in_list = participants.index(current_worker)
        if position_in_list == len(participants) - 1:
            return participants[0]
        else:
            return participants[position_in_list + 1]


    def __init__(
        self,
        dag,
        worker=None,
        participants=None,
        procedure=None,
        action_dirs=None,
        *args,**kwargs):

        self.worker = worker
        self.participants = participants
        self.procedure = procedure
        self.action_dirs = action_dirs

        super().__init__(
            dag,
            name='trigger-myself',
            python_callable=self.start,
            *args, **kwargs
        )
