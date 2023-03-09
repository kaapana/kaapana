import os
import sys
import uuid
from pathlib import Path
sys.path.insert(0, '../')
sys.path.insert(0, '/kaapana/app')
from kaapana_federated.KaapanaFederatedTraining import KaapanaFederatedTrainingBase, timeit

class FederatedSetupTestFederatedTraining(KaapanaFederatedTrainingBase):
    
    def __init__(self, workflow_dir=None, use_minio_mount=None):

        # make sure that workflow_dir is defined and get it from environmentals
        workflow_dir = os.getenv('WORKFLOW_DIR', None) if workflow_dir is None else workflow_dir
        assert workflow_dir

        super().__init__(workflow_dir=workflow_dir, use_minio_mount=use_minio_mount)

    @timeit  
    def update_data(self, federated_round, tmp_central_site_info):
        print(Path(self.fl_working_dir) / str(federated_round))
        print(tmp_central_site_info)
        print(federated_round)

    @timeit
    def on_wait_for_jobs_end(self, federated_round):
        self.run_in_parallel = True

if __name__ == "__main__":
    kaapana_ft = FederatedSetupTestFederatedTraining(use_minio_mount='/minio')
    kaapana_ft.train()
    kaapana_ft.clean_up_minio()
