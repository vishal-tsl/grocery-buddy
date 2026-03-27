from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""
    
    # Gemini API
    gemini_api_key: str
    
    # Autocomplete API
    autocomplete_auth_token: str = "adc3d49185744f4389a2183e694060b9"
    autocomplete_lat: float = 44.8828
    autocomplete_lng: float = -93.2007
    
    # App metadata
    app_name: str = "grocery-buddy"
    app_version: str = "1.0"
    
    # API Configuration
    autocomplete_base_url: str = "https://api.basketsavings.com/search2/search/suggested2"
    
    # Autocomplete API Options
    autocomplete_limit: int = 30  # Request more to filter for brand options
    autocomplete_include_images: bool = True
    autocomplete_exclude_subcategory: bool = False
    autocomplete_exclude_brand: bool = False  # Include brands in suggestions for user to choose

    # Admin tracking (Supabase)
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""
    admin_allowed_email: str = ""
    admin_panel_password: str = ""
    ip_geo_provider_url: str = "https://ip-api.com/json/{ip}?fields=status,country,regionName,city"
    tracking_enabled: bool = False
    tracking_retention_days: int = 30

    # GCS (Cloud Run: set GCS_BUCKET; uses attached service account / ADC)
    gcs_bucket: str = ""

    # Optional LLM re-rank of top-N autocomplete candidates (extra latency/cost)
    enable_llm_match_rerank: bool = False
    llm_rerank_top_n: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
