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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
