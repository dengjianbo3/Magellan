# backend/services/llm_gateway/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Define the environment variable to read
    GOOGLE_API_KEY: str

    # Load variables from a .env file
    model_config = SettingsConfigDict(env_file=".env")

# Create a single instance of the settings to be used across the application
settings = Settings()
