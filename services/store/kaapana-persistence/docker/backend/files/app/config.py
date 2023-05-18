from pydantic import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Kaapana Persistence API"
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "kaapana"
    schema_folder: str = "types"
    os_base_url: str = "http://opensearch-service.services.svc:9200"
    quido_base_url: str = "http://dcm4chee-service.services.svc:8080/dcm4chee-arc/aets"
    wado_base_url: str = "http://dcm4chee-service.services.svc:8080/dcm4chee-arc/aets"
    stow_root_url: str = "http://dcm4chee-service.services.svc:8080/dcm4chee-arc/aets"
    ohif_viewer: str = None  # "https://vm-128-212.cloud.dkfz-heidelberg.de/ohif/viewer"
    cas_root_path: str
    dev: bool = False
    base_url: str = "http://localhost:8000"


@lru_cache()
def get_settings():
    return Settings()
