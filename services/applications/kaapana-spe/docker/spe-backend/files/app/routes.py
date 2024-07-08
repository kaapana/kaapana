from fastapi import APIRouter

router = APIRouter()

# API-endpoints for the spe-extension.
# First step is to clarify what endpoints are actually needed.

# List search and filter available datasets.
# - list-dataset-specifications

# Apply for a specifica dataset(-specification?)
# - apply-for-dataset(-specification?) access

# Inspect data from a specific dataset? not sure if this is necessary
# - load-dataset

# - start spe 
#   - for vm-spe it is a call to airflow/trigger-workflow/... in theory it can be done by the frontend directly (if we want frontends to be able to talk to airflow directly, which feels questionable, but I don't have a specific example to argue against it)
#   - for currently this is also planned as call to airflow/... since the whole thing will be implemented via the KaapanaApplicationOperator. 
# - stop spe # 
#   - also call to application operator
# - list all sessions
    # TODO: ok where are all the sessions actually stored? 
# - 
# Some requests are answered by the backend directly, some are passed to the kaapana backend.

@router.post("/spe/apply/")
async def apply_for_dataset(application: Application):
    pass


@router.get("/spe/available-datasets")
async def list_dataset_specifications():
    pass

@router.get("/spe/available-datasets/query")
async def list_available_datasets():
    pass

@router.put("/spe/run/")
async def trigger_spe_dag_run():
    pass



