from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "SubText Backend"
    ENVIRONMENT: str = "local"
    API_KEY: str = "unsafe-secret-key"

    # Uvicorn Settings
    HOST: str = "0.0.0.0"  # Default to open for Docker/VM
    PORT: int = 80         # Default to 80 for your firewall
    RELOAD: bool = True    # Useful for dev, turn off in prod

    class Config:
        env_file = ".env"

settings = Settings()