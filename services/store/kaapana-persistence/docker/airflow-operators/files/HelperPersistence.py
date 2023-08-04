import requests


class CASClient:
    def __init__(self, cas_api_base_uri: str) -> None:
        self.base_url = cas_api_base_uri

    def upload(self, file) -> str:
        with open(file, "rb") as f:
            with requests.post(f"{self.base_url}/single", files={"file": f}) as r:
                r.raise_for_status()
                return r.text


class URNClient:
    def __init__(self, urn_api_base_uri: str) -> None:
        self.base_url = urn_api_base_uri

    def download(self, urn: str, target: str):
        with requests.get(f"{self.base_url}/{urn}") as r:
            r.raise_for_status()
            with open(target, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)


class KaapanaPersistenceClient:
    def __init__(self, persistence_api_base_uri: str) -> None:
        self.base_uri = persistence_api_base_uri

    def register_schema(self, schema) -> None:
        with requests.post(f"{self.base_uri}/schema/?exist_ok=true", json=schema) as r:
            r.raise_for_status()

    def store_object(self, schema, object) -> None:
        urn = schema["$id"]
        version = schema["version"]
        if not urn or not version:
            raise Exception("Invalid JSON Schema")
        with requests.post(f"{self.base_uri}/object/{urn}:{version}", json=object) as r:
            r.raise_for_status()
