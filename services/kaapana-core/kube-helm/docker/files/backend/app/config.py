from pydantic import BaseSettings
import os

class Settings(BaseSettings):
    """
    Configuration of the application

    Settings are populated using environment variables
    https://fastapi.tiangolo.com/advanced/settings/#pydantic-settings
    https://pydantic-docs.helpmanual.io/usage/settings/#environment-variable-names

    NOTE: Pydantic will read the environment variables in a case-insensitive way, 
          so, an upper-case variable APP_NAME will still be read for the attribute app_name
    """
    secret_key: str
    application_root: str

    helm_extensions_cache: str = "/root/extensions"
    helm_collections_cache: str = "/root/collections"
    kaapana_collections: str = os.getenv("KAAPANA_COLLECTIONS", "")
    prefetch_extensions: bool = True if os.environ.get('PREFETCH_EXTENSIONS', 'true') in ['true', 'True'] else False
    helm_helpers_cache: str = "/root/helpers"
    helm_namespace: str = os.getenv("HELM_NAMESPACE", "default")
    release_name: str = os.getenv("RELEASE_NAME") 
    registry_url: str

    offline_mode: bool = True if os.environ.get('OFFLINE_MODE', 'false') in ['true', 'True'] else False


settings = Settings()
