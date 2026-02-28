from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # API Settings
    api_title: str = "AI-Powered Document Intelligence API"
    api_version: str = "1.0.0"
    api_description: str = "A production-ready backend system for document intelligence"
    
    # Database Settings
    database_url: str = "postgresql://user:password@localhost:5432/doc_intelligence"
    redis_url: Optional[str] = "redis://localhost:6379"
    
    # LLM Settings
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: Optional[str] = os.getenv("LLM_BASE_URL")
    llm_default_model: str = "gpt-4-turbo"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096
    
    # Processing Settings
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    supported_file_types: list = ["application/pdf", "text/plain", "text/csv"]
    max_concurrent_processes: int = 5
    chunk_overlap_ratio: float = 0.1  # 10% overlap
    
    # Security Settings
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Paths
    upload_directory: str = "./uploads"
    processed_directory: str = "./processed"
    
    class Config:
        env_file = ".env"


settings = Settings()