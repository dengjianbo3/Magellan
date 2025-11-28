# backend/services/llm_gateway/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Gemini 配置
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"

    # Kimi 配置 (Moonshot AI)
    KIMI_API_KEY: Optional[str] = None
    KIMI_MODEL_NAME: str = "kimi-k2-0711-preview"
    KIMI_BASE_URL: str = "https://api.moonshot.cn/v1"

    # 默认提供商: "gemini" 或 "kimi"
    DEFAULT_LLM_PROVIDER: str = "gemini"

    # Load variables from a .env file
    model_config = SettingsConfigDict(env_file=".env")

# Create a single instance of the settings to be used across the application
settings = Settings()
