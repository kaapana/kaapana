import os
import sys
import uuid
from pathlib import Path
sys.path.insert(0, '../')
sys.path.insert(0, '/common')
from kaapana_federated.KaapanaFederatedTraining import KaapanaFederatedTrainingBase, requests_retry_session


class FederatedSetupTestFederatedTraining(KaapanaFederatedTrainingBase):
    
    def __init__(self, workflow_dir=None, use_minio_mount=None):
        super().__init__(workflow_dir=workflow_dir, use_minio_mount=use_minio_mount)
            
    def update_data(self, federated_round):
        print(Path(self.fl_working_dir) / str(federated_round))
        print(federated_round)

if __name__ == "__main__":
    kaapana_ft = FederatedSetupTestFederatedTraining(use_minio_mount='/minio')
    kaapana_ft.train()
