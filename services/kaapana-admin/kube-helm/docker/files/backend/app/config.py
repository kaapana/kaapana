from pydantic_settings  import BaseSettings
from pydantic import computed_field
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

    secret_key: str = os.getenv("SECRET_KEY", None)
    application_root: str = os.getenv("APPLICATION_ROOT", None)

    helm_extensions_cache: str = os.getenv("HELM_EXTENSIONS_CACHE", None)
    helm_platforms_cache: str = os.getenv("HELM_PLATFORMS_CACHE", None)
    helm_collections_cache: str = "/root/collections"
    kaapana_collections: str = os.getenv("KAAPANA_COLLECTIONS", None)
    prefetch_extensions: bool = (
        True
        if os.environ.get("PREFETCH_EXTENSIONS", None) in ["true", "True"]
        else False
    )
    helm_helpers_cache: str = "/root/helpers"
    helm_namespace: str = os.getenv("HELM_NAMESPACE", None)
    release_name: str = os.getenv("RELEASE_NAME", None)
    registry_url: str = os.getenv("REGISTRY_URL", None)

    offline_mode: bool = (
        True if os.environ.get("OFFLINE_MODE", None) in ["true", "True"] else False
    )
    kubectl_path: str = os.getenv("KUBECTL_PATH", None)
    helm_path: str = os.getenv("HELM_PATH", None)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    recent_update_cache: bool = (
        True
        if os.environ.get("RECENT_UPDATE_CACHE", None) in ["true", "True"]
        else False
    )  # TODO: delete
    containerd_sock: str = os.getenv("CONTAINERD_SOCK", None)


class TimeoutConfig(BaseSettings):
    shell_cmd_default_timeout: int = 10  # 5
    helm_pull_container_timeout: int = 2 * 60 * 60
    helm_install_timeout: int = 15
    helm_deletion_timeout: int = 20

    # old: helm_install_platform_timeout: int = 45
    @computed_field
    @property
    def helm_install_platform_timeout(self) -> int:
        return self.helm_install_timeout * 3

    # old: helm_deletion_platform_timeout: int = 60
    @computed_field
    @property
    def helm_deletion_platform_timeout(self) -> int:
        return self.helm_deletion_timeout * 3


timeouts = TimeoutConfig()
settings = Settings()
