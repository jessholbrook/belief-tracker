from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 16384
    db_path: str = "./data/app.db"
    allowed_origins: str = "http://localhost:5173,http://localhost:8080"
    log_level: str = "INFO"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
