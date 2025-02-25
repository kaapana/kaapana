import os

POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_HOST = f"notifications-postgres-service.services.svc"
POSTGRES_PORT = f"5432"
DATABASE_NAME = "postgres"
