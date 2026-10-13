import functools

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Base url where WOPI Server can reach collabora server
    collabora_url: str
    # If this regex is matching documents in the path they are ignored
    document_path_ignore_regex: str = r"(.*\.minio\.sys)|(.*thumbnail)"
    # Endpoint for Collabra to acess WOPI API
    wopi_api_endpoint: str = "localhost:5000"
    minio_url: str
    discovery_interval_seconds: float = 60
    discovery_retry_seconds: float = 5
    ui_directory: str = "ui/dist"
    # Dev Mode enables more verbose logging and CORS from multiple hosts
    dev_mode: bool = False


@functools.lru_cache()
def get_settings():
    return Settings()
