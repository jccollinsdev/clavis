from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    minimax_api_key: str
    sentry_dsn: str = ""
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.0
    sentry_profiles_sample_rate: float = 0.0
    cors_allowed_origins: str = "https://clavis.andoverdigital.com"
    enable_public_docs: bool = False
    admin_password: str = ""
    admin_session_secret: str = ""
    minimax_base_url: str = "https://api.minimax.io/v1"
    finnhub_api_key: str = ""
    apns_key_id: str = ""
    apns_team_id: str = ""
    apns_key_path: str = "/app/apns.p8"
    apns_bundle_id: str = "com.clavisdev.portfolioassistant"
    polygon_api_key: str = ""

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache
def get_settings() -> Settings:
    return Settings()
