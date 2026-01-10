"""Configuration management for the interior design agent."""
import os
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration."""

    # Anthropic API
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Embedding configuration
    EMBEDDING_PROVIDER: Literal["voyage", "openai", "huggingface"] = os.getenv("EMBEDDING_PROVIDER", "huggingface")
    VOYAGE_API_KEY: str = os.getenv("VOYAGE_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))

    # Image generation
    IMAGE_GENERATOR: Literal["gpt-image-1.5", "banana-pro", "placeholder"] = os.getenv(
        "IMAGE_GENERATOR", "placeholder"
    )
    IMAGE_API_KEY: str = os.getenv("IMAGE_API_KEY", "")
    IMAGE_ENDPOINT: str = os.getenv("IMAGE_ENDPOINT", "")
    IMAGE_MODEL_KEY: str = os.getenv("IMAGE_MODEL_KEY", "")

    # Paths
    CHROMA_DB_PATH: Path = Path(os.getenv("CHROMA_DB_PATH", "./chroma_db"))
    DATA_STORAGE_PATH: Path = Path(os.getenv("DATA_STORAGE_PATH", "./data"))

    # App settings
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Claude model settings
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    CLAUDE_MAX_TOKENS: int = 4096

    # Memory settings
    CHAT_MEMORY_TOKEN_LIMIT: int = 4096
    SIMILARITY_TOP_K: int = 5
    PREFERENCE_CONFIDENCE_THRESHOLD: float = 0.5

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required")

        if cls.EMBEDDING_PROVIDER == "voyage" and not cls.VOYAGE_API_KEY:
            raise ValueError("VOYAGE_API_KEY is required when using Voyage embeddings")

        if cls.EMBEDDING_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI embeddings")

        # HuggingFace embeddings don't require API keys - they run locally

        # Create directories if they don't exist
        cls.CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
        cls.DATA_STORAGE_PATH.mkdir(parents=True, exist_ok=True)


# Create config instance
config = Config()
