import os
import sys
import uuid
from pathlib import Path
sys.path.insert(0, '../')
sys.path.insert(0, '/kaapanasrc')
from kaapana_federated.KaapanaFederatedTraining import KaapanaFederatedTrainingBase, timeit

class FederatedSetupTestFederatedTraining(KaapanaFederatedTrainingBase):
    
    def __init__(self, workflow_dir=None, use_minio_mount=None, use_threading=True):
        super().__init__(workflow_dir=workflow_dir, use_minio_mount=use_minio_mount, use_threading=use_threading)

    @timeit  
    def update_data(self, federated_round, tmp_central_site_info):
        print(Path(self.fl_working_dir) / str(federated_round))
        print(tmp_central_site_info)
        print(federated_round)

if __name__ == "__main__":
    kaapana_ft = FederatedSetupTestFederatedTraining(use_minio_mount='/minio', use_threading=True)
    kaapana_ft.train()
    kaapana_ft.clean_up_minio()
