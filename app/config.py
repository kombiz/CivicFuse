"""Application configuration management."""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database configuration
    database_url: str
    postgres_host: str = "100.101.93.9"
    postgres_port: int = 5434
    postgres_user: str = "postgres"
    postgres_password: str
    postgres_db: str = "advocacy_cms"
    
    # Connection pool settings
    db_pool_size: int = 10
    db_pool_max_overflow: int = 20
    db_pool_timeout: int = 30
    
    # Application settings
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # API configuration
    api_v1_prefix: str = "/api/v1"
    
    # UI configuration
    templates_dir: str = "app/templates"
    static_dir: str = "app/static"
    
    # External services (for future use)
    bluesky_api_url: str = "https://bsky.social/xrpc"
    meltwater_api_url: str = "https://api.meltwater.com"
    meltwater_api_key: Optional[str] = None
    ollama_api_url: str = "http://ollama:11434"
    
    # Feature flags
    enable_ai_analysis: bool = False
    enable_social_monitoring: bool = False
    enable_email_notifications: bool = False
    
    # Performance settings
    cache_ttl: int = 300
    request_timeout: int = 30
    
    # Security settings
    rate_limit_per_minute: int = 60
    allowed_origins: str = "http://localhost:8000,http://localhost:3000"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env.lower() == "production"
    
    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse allowed origins into a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

# Create a global settings instance
settings = get_settings()