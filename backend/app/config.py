from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    # Optional shared bearer token. When set, all /api routes (except
    # /api/health) and the chat WebSocket require it.
    api_auth_token: str = ""
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 16384
    db_path: str = "./data/app.db"
    allowed_origins: str = "http://localhost:5173,http://localhost:8080"
    # Optional regex for matching dynamic origins (e.g. Vercel preview URLs).
    allowed_origin_regex: str | None = None
    log_level: str = "INFO"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
