from pydantic import BaseSettings


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
    namespace: str = "default"

    helm_extensions_cache: str = "/root/charts/extensions"
    helm_collections_cache: str = "/root/charts/collections"
    helm_helpers_cache: str = "/root/charts/helpers"

    registry_url: str

    offline_mode: bool


settings = Settings()
