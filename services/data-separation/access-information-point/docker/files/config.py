import os

POSTGRES_USERNAME = os.getenv('POSTGRES_USERNAME', 'kaapanauser')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password')
POSTGRES_HOST = f"aip-postgres-service.services.svc"
POSTGRES_PORT = f"5432"

DATABASE_NAME = 'access_information_point'