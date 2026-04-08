"""Global configuration for Raggy, loaded from .env and optional config.yaml."""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KB_ROOT = PROJECT_ROOT / "knowledge_base"
CHROMA_PERSIST_DIR = KB_ROOT / "chroma_db"
PROMPTS_DIR = KB_ROOT / "prompts"
LOG_DIR = PROJECT_ROOT / "logs"


class Settings(BaseSettings):
    # LLM Provider
    llm_provider: str = Field(default="ollama", description="LLM provider: anthropic, openai, google, ollama")
    llm_model: str = Field(default="gemma3:4b", description="Model name")

    # API Keys
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    openai_api_key: str = Field(default="", description="OpenAI API key")
    google_api_key: str = Field(default="", description="Google API key")

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama base URL")

    # Embeddings
    embedding_provider: str = Field(default="local", description="Embedding provider: local, openai, ollama")
    embedding_model: str = Field(default="paraphrase-multilingual-MiniLM-L12-v2", description="Embedding model name")

    # Generation parameters
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    max_tokens: int = Field(default=4096, ge=512, le=8192)

    # Hugging Face (optional — avoids rate limits when downloading embedding models)
    hf_token: str = Field(default="", description="Hugging Face access token (optional)")

    # Admin
    admin_password: str = Field(default="changeme", description="Admin panel password")

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


# Mapping: Settings field name → .env variable name
_FIELD_TO_ENV: dict[str, str] = {
    "llm_provider": "LLM_PROVIDER",
    "llm_model": "LLM_MODEL",
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "openai_api_key": "OPENAI_API_KEY",
    "google_api_key": "GOOGLE_API_KEY",
    "ollama_base_url": "OLLAMA_BASE_URL",
    "embedding_provider": "EMBEDDING_PROVIDER",
    "embedding_model": "EMBEDDING_MODEL",
    "temperature": "TEMPERATURE",
    "max_tokens": "MAX_TOKENS",
    "hf_token": "HF_TOKEN",
    "admin_password": "ADMIN_PASSWORD",
}


def save_settings_to_env(updates: dict) -> None:
    """Persist selected settings to .env so they survive restarts.

    Parameters
    ----------
    updates:
        Dict of {field_name: value}, e.g. {"llm_provider": "ollama", "llm_model": "gemma3:4b"}.
        API keys are written only if non-empty.
    """
    env_file = PROJECT_ROOT / ".env"

    # Read existing key=value pairs
    existing: dict[str, str] = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k, _, v = stripped.partition("=")
                existing[k.strip()] = v.strip()

    # Apply updates
    for field, value in updates.items():
        env_key = _FIELD_TO_ENV.get(field, field.upper())
        # Don't write empty API keys (would overwrite a valid existing key)
        if "api_key" in field and not value:
            continue
        existing[env_key] = str(value)

    # Write back
    with open(env_file, "w", encoding="utf-8") as f:
        for k, v in sorted(existing.items()):
            f.write(f"{k}={v}\n")
