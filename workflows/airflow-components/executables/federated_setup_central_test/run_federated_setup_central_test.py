import os
import sys
import uuid
from pathlib import Path
sys.path.insert(0, '../')
sys.path.insert(0, '/executables')
from kaapana_federated.kaapana_federated import KaapanaFederatedTrainingBase, requests_retry_session


class FederatedSetupTestFederatedTraining(KaapanaFederatedTrainingBase):
    
    def __init__(self, workflow_dir=None):
        super().__init__(workflow_dir)
            
    def update_data(self, federated_round):
        print(Path(self.fl_working_dir) / str(federated_round))
        print(federated_round)

if __name__ == "__main__":
    kaapana_ft = FederatedSetupTestFederatedTraining()
    kaapana_ft.train()
