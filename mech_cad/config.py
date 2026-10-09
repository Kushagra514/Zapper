"""Configuration management with fallback for any environment."""

from pathlib import Path
import os

try:
    from pydantic_settings import BaseSettings
    class Settings(BaseSettings):
        PROJECT_NAME: str = "MECH AI ADDON"
        VERSION: str = "0.1.0"
        DEBUG: bool = False

        OPENAI_API_KEY: str | None = None
        GOOGLE_API_KEY: str | None = None
        ANTHROPIC_API_KEY: str | None = None
        OLLAMA_BASE_URL: str = "http://localhost:11434"

        DEFAULT_VISION_PROVIDER: str = "ollama"
        DEFAULT_VISION_MODEL: str = "llama3.2-vision:11b"
        DEFAULT_TEXT_PROVIDER: str = "ollama"
        DEFAULT_TEXT_MODEL: str = "mistral:7b"

        DATABASE_URL: str = "sqlite:///./data/mech_cad.db"
        ARTIFACT_STORE_PATH: Path = Path("./data/artifacts")
        ARTIFACT_STORE_BACKEND: str = "local"

        REDIS_URL: str = "redis://localhost:6379/0"

        AUTH_DISABLED: bool = True
        API_SECRET_KEY: str = "dev-secret-key-change-in-prod"

        JOB_TIMEOUT_SECONDS: int = 600
        CAD_EXEC_TIMEOUT_SECONDS: int = 60
        MAX_UPLOAD_BYTES: int = 52428800
        MAX_CONCURRENT_JOBS: int = 4

        LOG_LEVEL: str = "INFO"

    settings = Settings()
except Exception:
    from dataclasses import dataclass

    @dataclass
    class Settings:
        PROJECT_NAME: str = "MECH AI ADDON"
        VERSION: str = "0.1.0"
        DEBUG: bool = False

        OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
        GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
        ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
        OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        DEFAULT_VISION_PROVIDER: str = os.getenv("DEFAULT_VISION_PROVIDER", "ollama")
        DEFAULT_VISION_MODEL: str = os.getenv("DEFAULT_VISION_MODEL", "llama3.2-vision:11b")
        DEFAULT_TEXT_PROVIDER: str = os.getenv("DEFAULT_TEXT_PROVIDER", "ollama")
        DEFAULT_TEXT_MODEL: str = os.getenv("DEFAULT_TEXT_MODEL", "mistral:7b")

        DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/mech_cad.db")
        ARTIFACT_STORE_PATH: Path = Path(os.getenv("ARTIFACT_STORE_PATH", "./data/artifacts"))
        ARTIFACT_STORE_BACKEND: str = os.getenv("ARTIFACT_STORE_BACKEND", "local")

        REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        AUTH_DISABLED: bool = os.getenv("AUTH_DISABLED", "true").lower() == "true"
        API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "dev-secret-key-change-in-prod")

        JOB_TIMEOUT_SECONDS: int = int(os.getenv("JOB_TIMEOUT_SECONDS", "600"))
        CAD_EXEC_TIMEOUT_SECONDS: int = int(os.getenv("CAD_EXEC_TIMEOUT_SECONDS", "60"))
        MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", "52428800"))
        MAX_CONCURRENT_JOBS: int = int(os.getenv("MAX_CONCURRENT_JOBS", "4"))

        LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    settings = Settings()
