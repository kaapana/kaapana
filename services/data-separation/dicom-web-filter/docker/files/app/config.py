import os

DICOMWEB_BASE_URL = os.environ["DICOMWEB_BASE_URL"]
DICOMWEB_BASE_URL_WADO_URI = os.environ["DICOMWEB_BASE_URL_WADO_URI"]

POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_HOST = f"aip-postgres-service.services.svc"
POSTGRES_PORT = f"5432"
DATABASE_NAME = "access_information_point"
