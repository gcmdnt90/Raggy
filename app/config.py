"""Global configuration, loaded from `.env`.

There is no `config.yaml`; this docstring claimed one for as long as the file has
existed in Banco, inherited from Raggy along with the settings themselves.
"""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from app.i18n import t
from app.utils.network import normalize_ollama_base_url

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
    #: The default ceiling for a role whose session profile states no
    #: `max_tokens`. Unbounded above on purpose (ADR 0005): the `le=4000` this
    #: used to carry was an inherited Raggy rail that made an Anthropic thinking
    #: budget arithmetically impossible, since the budget must be at least 1024
    #: and strictly below `max_tokens`. Banco is run by the person who owns the
    #: key; the ceiling was protecting them from their own usage.
    max_tokens: int = Field(default=1500, ge=512)
    #: Kept as a figure to *display*, never to enforce. `remaining_budget()`
    #: still answers, and nothing refuses a call on the strength of it.
    daily_token_budget: int = Field(default=200000, ge=1000)

    # Hugging Face (optional — avoids rate limits when downloading embedding models)
    hf_token: str = Field(default="", description="Hugging Face access token (optional)")

    # Session profile — the named file in demo/sessions/ that binds each role
    # to a provider, model and parameters. One scalar, written by the console.
    # Absent or unreadable falls back to the derived binding, so an existing
    # install keeps working and a corrupt profile degrades rather than blocks
    # (ADR 0004).
    session_profile: str = Field(default="", description="Active session profile name")

    # Admin
    admin_password: str = Field(default="changeme", description="Admin panel password")

    @field_validator("ollama_base_url")
    @classmethod
    def _validate_ollama_base_url(cls, value: str) -> str:
        """Reject a non-loopback or credentialed Ollama target at load time.

        OLLAMA_BASE_URL comes from .env and reaches requests unmodified, so an
        unchecked value is a server-side request forgery primitive. Failing
        here means a bad value surfaces during pre-flight on the stage console,
        where a trainer can act on it, rather than mid-demonstration.

        A deliberate remote Ollama is not supported by this field yet: it would
        send every prompt off the machine, so it needs an explicit setting and
        an egress indicator that shows it, not a quiet exception here.
        """
        return normalize_ollama_base_url(value)

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def get_settings() -> Settings:
    """Build a fresh Settings, re-reading `.env` each time.

    Not cached, whatever the name suggests — and the lack of a cache is what the
    stage console depends on: it writes a key to `.env` and the very next request
    has to see it, with nothing to invalidate. The docstring said "cached" until
    2026-09-13, which is the opposite of what the function does and of what
    `app/server/console.py` relies on.
    """
    return Settings()


# Mapping: Settings field name → .env variable name
_FIELD_TO_ENV: dict[str, str] = {
    "llm_provider": "LLM_PROVIDER",
    "llm_model": "LLM_MODEL",
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "openai_api_key": "OPENAI_API_KEY",
    "google_api_key": "GOOGLE_API_KEY",
    "ollama_base_url": "OLLAMA_BASE_URL",
    "session_profile": "SESSION_PROFILE",
    "embedding_provider": "EMBEDDING_PROVIDER",
    "embedding_model": "EMBEDDING_MODEL",
    "temperature": "TEMPERATURE",
    "max_tokens": "MAX_TOKENS",
    "daily_token_budget": "DAILY_TOKEN_BUDGET",
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
        text = str(value)
        # `.env` is line-oriented and written back verbatim below, so a value
        # carrying a newline would define a second variable. Every caller —
        # the console, the setup wizard — takes these from human input, so the
        # guard lives here rather than being repeated at each one.
        if any(char in text for char in "\r\n\x00"):
            raise ValueError(t("config.env.line_break", key=env_key))
        existing[env_key] = text

    # Write back
    with open(env_file, "w", encoding="utf-8") as f:
        for k, v in sorted(existing.items()):
            f.write(f"{k}={v}\n")
