import os
from airflow.api.common.experimental.pool import get_pool

BATCH_NAME = "batch"
AIRFLOW_WORKFLOW_DIR = "/kaapana/mounted/workflows/data"
PROCESSING_WORKFLOW_DIR = "/kaapana/mounted/data"
INSTANCE_NAME = os.getenv("INSTANCE_NAME", None)
KAAPANA_BUILD_VERSION = os.getenv("KAAPANA_BUILD_VERSION", None)
ADMIN_NAMESPACE = os.getenv("ADMIN_NAMESPACE", None)
SERVICES_NAMESPACE = os.getenv("SERVICES_NAMESPACE", None)
JOBS_NAMESPACE = os.getenv("JOBS_NAMESPACE", None)
EXTENSIONS_NAMESPACE = os.getenv("EXTENSIONS_NAMESPACE", None)
PULL_POLICY_IMAGES = os.getenv("PULL_POLICY_IMAGES", "IfNotPresent")
DEFAULT_REGISTRY = os.getenv("DEFAULT_REGISTRY", None)
KAAPANA_BUILD_VERSION = os.getenv("KAAPANA_BUILD_VERSION", None)
PLATFORM_VERSION = os.getenv("PLATFORM_VERSION", None)
GPU_SUPPORT = True if os.getenv("GPU_SUPPORT", "False").lower() == "true" else False
ENABLE_NFS = os.getenv("ENABLE_NFS", None)
SMTP_HOST = os.getenv("SMTP_HOST", None)
SMTP_PORT = os.getenv("SMTP_PORT", 0)
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", None)
SMTP_USERNAME = os.getenv("SMTP_USERNAME", None)
EMAIL_ADDRESS_SENDER = os.getenv("EMAIL_ADDRESS_SENDER", None)

# Deprecated kept for backwards compatibility
WORKFLOW_DIR = AIRFLOW_WORKFLOW_DIR
BUILD_VERSION = KAAPANA_BUILD_VERSION

try:
    GPU_COUNT = int(get_pool(name="NODE_GPU_COUNT").slots)
except Exception as e:
    GPU_COUNT = 0

try:
    CPU_CORE_COUNT = int(get_pool(name="NODE_CPU_CORES").slots)
except Exception as e:
    CPU_CORE_COUNT = 1
