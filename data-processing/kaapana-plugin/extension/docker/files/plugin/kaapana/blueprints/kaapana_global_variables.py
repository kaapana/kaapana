import os
BATCH_NAME = 'batch'
WORKFLOW_DIR = 'data'
INSTANCE_NAME = os.getenv('INSTANCE_NAME', None)
INSTANCE_ID = os.getenv('INSTANCE_ID', None)

assert INSTANCE_NAME
assert INSTANCE_ID
