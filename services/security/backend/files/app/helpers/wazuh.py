
from typing import Optional
import httpx

class WazuhAPIAuthenication():
    # todo handle expiration of token
    __jwt_token: str = ""

    def retrieve_token(self) -> bool:
        headers = {"Content-Type": "application/json", "Authorization":"Basic d2F6dWgtd3VpOk15UzNjcjM3UDQ1MHIuKi0="} # todo: replace basic credentials with randomly generated one and pass from deployment as env var
        result = httpx.get("https://security-wazuh-service.services.svc:55000/security/user/authenticate", verify=False, headers=headers)
        print(f"wazuh auth result: {result}")
        self.__jwt_token = result.json()["data"]["token"]

    def get_bearer_token(self) -> Optional[str]:
        if not self.__jwt_token and not self.retrieve_token():
            return None
        print(f"wazuh token: {self.__jwt_token}")
        return f"Bearer {self.__jwt_token}"
