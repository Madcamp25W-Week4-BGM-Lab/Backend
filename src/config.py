from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "SubText Backend"
    ENVIRONMENT: str = "local"
    API_KEY: str = "unsafe-secret-key"

    class Config:
        env_file = ".env"

settings = Settings()