"""Configuration management for Video-Generate backend."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/video_generate"
    redis_url: str = "redis://localhost:6379/0"

    # LLM / AI
    llm_api_key: str = "sk-orx-EATWLx2onAWQfkJpRj5zOhluXYACY5hm"
    llm_api_url: str = "http://10.190.0.214:8080/v1"
    llm_model: str = "deepseek-v4-pro"

    # External services
    comfyui_url: str = "http://10.190.0.222:8188"
    cosyvoice_url: str = "http://10.190.0.222:8000"
    sd_api_url: str = "http://10.190.0.222:7860"

    # Paths
    upload_dir: str = "/data/uploads"
    output_dir: str = "/data/output"

    # JWT
    jwt_secret: str = "change-me-to-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 86400  # 24 hours in seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
