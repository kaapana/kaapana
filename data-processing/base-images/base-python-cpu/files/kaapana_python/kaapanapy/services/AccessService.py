import requests
from kaapanapy.settings import ServicesSettings

access_settings = ServicesSettings()


class AccessService:
    def __init__(self, base_url: str = access_settings.aii_url):
        self.base_url = base_url

    async def fetch_user_ids(
        self, project_id: str, include_system: bool = False
    ) -> list[str]:
        response = requests.get(f"{self.base_url}/projects/{project_id}/users")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        try:
            data = response.json()
        except requests.JSONDecodeError:
            data = []

        return [user["id"] for user in data if not user["system"] or include_system]

    async def user_exists(self, user_id: str) -> bool:
        response = requests.get(f"{self.base_url}/users/{user_id}")
        if response.status_code < 300:
            return True
        elif response.status_code == 404:
            return False
        else:
            response.raise_for_status()
            raise Exception("THis should not happen")
