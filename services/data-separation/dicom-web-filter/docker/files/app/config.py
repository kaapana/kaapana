import os

DICOMWEB_BASE_URL = os.environ["DICOMWEB_BASE_URL"]
DICOMWEB_BASE_URL_WADO_URI = os.environ["DICOMWEB_BASE_URL_WADO_URI"]

POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_HOST = f"dicom-project-mapping-postgres-service.services.svc"
POSTGRES_PORT = f"5432"
DATABASE_NAME = "dicom_project_mapping"

ACCESS_INFORMATION_INTERFACE_HOST = f"aii-service.services.svc"
ACCESS_INFORMATION_INTERFACE_PORT = f"8080"