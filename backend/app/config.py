"""Configuration management for Video-Generate backend."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@db:5432/video_generate"
    redis_url: str = "redis://redis:6379/0"
    llm_api_key: str = ""
    llm_api_url: str = "http://10.190.0.214:8080/v1"
    llm_model: str = "deepseek-v4-pro"
    comfyui_url: str = "http://10.190.0.222:8188"
    cosyvoice_url: str = "http://10.190.0.222:8000"
    upload_dir: str = "/data/uploads"
    output_dir: str = "/data/output"
    jwt_secret: str = "change-me-to-random-secret"

    class Config:
        env_file = ".env"


settings = Settings()
