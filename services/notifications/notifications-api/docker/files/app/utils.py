import os

import requests

SERVICE_NAMESPACE = os.getenv("SERVICES_NAMESPACE")


class AiiHelper:
    def __init__(self):
        self.base_url = f"http://aii-service.{SERVICE_NAMESPACE}.svc:8080"

    async def fetch_project_users(
        self, project_name: str, id_only: bool = True
    ) -> list:
        response = requests.get(f"{self.base_url}/projects/{project_name}/users")
        response.raise_for_status()
        try:
            data = response.json()
        except requests.JSONDecodeError:
            data = []

        users = []
        if id_only:
            users = [user["id"] for user in data]
        else:
            users = data

        return users


def get_aii_helper() -> AiiHelper:
    return AiiHelper()
