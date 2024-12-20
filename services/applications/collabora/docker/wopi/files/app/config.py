import functools
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Base url where WOPI Server can reach collabora server
    collabora_url: str = None
    # Root path to scann for documents
    document_root: str = None
    # If this regex is matching documents in the path they are ignored
    document_path_ignore_regex: str = "(.*\.minio\.sys)|(.*thumbnail)"
    # Endpoint for Collabra to acess WOPI API
    wopi_api_endpoint: str = "http://localhost:5000/wopi"
    # Dev Mode enables more verbose logging and CORS from multiple hosts
    dev_mode: bool = True


@functools.lru_cache()
def get_settings():
    return Settings()
