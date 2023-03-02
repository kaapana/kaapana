import os
from airflow.api.common.experimental.pool import get_pool

BATCH_NAME = 'batch'
AIRFLOW_WORKFLOW_DIR = '/kaapana/mounted/workflows/data'
PROCESSING_WORKFLOW_DIR = '/kaapana/mounted/data'
INSTANCE_NAME = os.getenv('INSTANCE_NAME', None)
assert INSTANCE_NAME
ADMIN_NAMESPACE = os.getenv('ADMIN_NAMESPACE', None)
assert ADMIN_NAMESPACE
SERVICES_NAMESPACE = os.getenv('SERVICES_NAMESPACE', None)
assert SERVICES_NAMESPACE
JOBS_NAMESPACE = os.getenv('JOBS_NAMESPACE', None)
assert JOBS_NAMESPACE
EXTENSIONS_NAMESPACE = os.getenv('EXTENSIONS_NAMESPACE', None)
assert EXTENSIONS_NAMESPACE

try:
    GPU_COUNT = int(get_pool(name="NODE_GPU_COUNT").slots)
except Exception as e:
    GPU_COUNT = 0

try:
    CPU_CORE_COUNT = int(get_pool(name="NODE_CPU_CORES").slots)
except Exception as e:
    CPU_CORE_COUNT = 1
    
