from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    AII_URL: str


settings = Settings()
