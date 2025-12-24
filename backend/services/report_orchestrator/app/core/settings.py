"""
Application Settings
应用配置

统一管理所有环境变量和配置项
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Service Discovery
    llm_gateway_url: str = "http://llm_gateway:8003"
    external_data_url: str = "http://external_data_service:8006"
    file_service_url: str = "http://file_service:8001"
    user_service_url: str = "http://user_service:8008"

    # Redis
    redis_url: str = "redis://redis:6379"

    # Qdrant Vector Store
    qdrant_url: str = "http://qdrant:6333"

    # Kafka
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_enabled: bool = True

    # Logging
    log_level: str = "INFO"
    json_logs: bool = False

    # Application
    app_name: str = "report_orchestrator"
    app_version: str = "3.0.0"
    debug: bool = False

    # Timeouts (seconds)
    llm_timeout: int = 180
    http_timeout: int = 300

    class Config:
        env_prefix = ""
        case_sensitive = False
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience accessors
settings = get_settings()
