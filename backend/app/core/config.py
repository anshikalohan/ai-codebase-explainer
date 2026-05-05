"""
Application configuration using environment variables.
"""

import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # API Keys
    GROQ_API_KEY: str = ""

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://your-frontend-domain.vercel.app",
    ]

    # Vector Store
    VECTOR_STORE_PATH: str = "./data/vector_store"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # LLM
    GROQ_MODEL: str = "llama3-70b-8192"
    MAX_TOKENS: int = 2048
    TEMPERATURE: float = 0.1

    # RAG
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    TOP_K_RESULTS: int = 6
    MAX_FILE_SIZE_MB: int = 50
    MAX_CONTEXT_FILES: int = 200

    # Cache
    CACHE_TTL_SECONDS: int = 3600
    MAX_CACHE_SIZE: int = 128

    # Ignored paths
    IGNORED_DIRS: List[str] = [
        "node_modules", ".git", "__pycache__", ".next", "dist",
        "build", "venv", ".venv", "env", ".env", "coverage",
        ".pytest_cache", ".mypy_cache", "target", "vendor",
        ".idea", ".vscode", "out", ".cache"
    ]

    IGNORED_EXTENSIONS: List[str] = [
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
        ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z",
        ".mp4", ".mp3", ".avi", ".mov", ".woff", ".woff2",
        ".ttf", ".eot", ".bin", ".exe", ".dll", ".so",
        ".pyc", ".pyo", ".class", ".jar", ".lock"
    ]

    SUPPORTED_EXTENSIONS: List[str] = [
        ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp",
        ".h", ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".swift",
        ".kt", ".scala", ".r", ".sh", ".bash", ".zsh", ".sql",
        ".html", ".css", ".scss", ".sass", ".less", ".vue",
        ".md", ".mdx", ".json", ".yaml", ".yml", ".toml",
        ".xml", ".env.example", ".dockerfile", "Dockerfile",
        ".tf", ".hcl", ".gradle", "Makefile", "Cargo.toml",
        "pyproject.toml", "package.json", "requirements.txt"
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
