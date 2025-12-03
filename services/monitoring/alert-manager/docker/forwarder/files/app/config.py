from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    log_level: str = Field(alias="LOG_LEVEL")
    aii_base_url: str = Field(alias="AII_BASE_URL")
    notification_service_url: str = Field(alias="NOTIFICATION_SERVICE_URL")
    admin_project_cache_ttl: int = Field(alias="ADMIN_PROJECT_CACHE_TTL")
    topic_prefix: str = Field(alias="TOPIC_PREFIX")
    default_icon: str = Field(alias="FORWARDER_DEFAULT_ICON")
    http_timeout: float = Field(alias="HTTP_TIMEOUT")
    http_connect_timeout: float = Field(alias="HTTP_CONNECT_TIMEOUT")


settings = Settings()
