from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Matchr Backend"
    app_env: str = "development"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:3000"
    frontend_url: str = "http://localhost:3000"
    port: int = 4000

    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # User auth lives on Xano (JWT via /auth/signup, /auth/login, /auth/me).
    # Job-catalog calls stay on ai-service; this URL is only for user identity.
    xano_api_url: str = ""
    xano_auth_api_url: str = ""
    # "" = require auth only when the Authentication endpoints exist on the group.
    # "true" / "false" force the gate on or off.
    xano_auth_required: str = ""

    ai_service_url: str = "http://localhost:8080"
    matchr_service_secret: str = "matchr-dev"

    serpapi_api_key: str = ""
    nutrient_api_key: str = ""
    kong_gateway_url: str = ""
    namecom_api_key: str = ""
    namecom_username: str = ""
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_redirect_uri: str = "http://localhost:4000/api/integrations/linkedin/callback"
    # Optional DMA Member Snapshot scope, e.g. r_dma_portability_3rd_party.
    # Leave empty unless the LinkedIn app has Member Data Portability enabled.
    linkedin_dma_scope: str = ""
    gmail_client_id: str = ""
    gmail_client_secret: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
