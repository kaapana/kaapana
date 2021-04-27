import os
import time
import json
import requests
import shutil

from minio import Minio

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator, rest_self_udpate
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class AwaitingModelsOperator(KaapanaPythonBaseOperator):

    @rest_self_udpate
    def start(self, ds, **kwargs):

        assert self.procedure in ['avg', 'seq'], 'You have to provide either "avg" or "seq" as procedure - stopping...'

        # only needed for initial dag run (worker not yet given as global value)
        if self.worker is None and self.procedure == 'seq':
            self.worker = self.participants[0]
            print('Set initial worker to {}'.format(self.worker))

        # Minio client
        access_key = os.environ.get('MINIOUSER')
        secret_key = os.environ.get('MINIOPASSWORD')
        session_token = None
        
        minio_client = Minio(
            self.minio_host + ":" + self.minio_port,
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token,
            secure=False
        )

        # Determine for which worker(s) to wait for
        participants = self.participants if self.procedure == 'avg' else [self.worker]
        
        print('Waiting for model(s) from participant(s) ({}) - checking every {} seconds'.format(participants, self.check_minio_interval))
        print('...')
        while not self.check_availability(minio_client, participants):
            time.sleep(self.check_minio_interval)
        
        print('Minio recieved model(s) from particpant(s) ({})'.format(participants))
    
    
    def check_availability(self, minio_client, participants, folder='cache'):
        """Returns True when all models are available in Minio - else, False"""
        
        response = minio_client.list_objects(self.bucket_name, prefix=f'{folder}/')
        content = [element.object_name for element in response]

        model_list = [f'{folder}/model_checkpoint_from_{participant}.pt' for participant in participants]
        available = [model_file_path in content for model_file_path in model_list]
        return all(available)


    def __init__(
        self,
        dag,
        worker=None,
        procedure=None,
        participants=None,
        bucket_name=None,
        *args,**kwargs):

        self.minio_host = 'minio-service.store.svc'
        self.minio_port = '9000'

        self.worker = worker
        self.procedure = procedure
        self.participants = participants
        self.bucket_name = bucket_name
        self.check_minio_interval = 15 # seconds

        super().__init__(
            dag,
            name='awating-models',
            python_callable=self.start,
            *args, **kwargs
        )
