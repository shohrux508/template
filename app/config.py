from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Единая конфигурация приложения.

    Все значения загружаются из .env и доступны через ``from app.config import settings``.
    """

    # ── Запуск компонентов ───────────────────────────────────────────────
    RUN_TELEGRAM: bool = True
    RUN_API: bool = True

    # ── Telegram ─────────────────────────────────────────────────────────
    BOT_TOKEN: str | None = None

    # ── API ──────────────────────────────────────────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # ── AI / LLM ─────────────────────────────────────────────────────────
    LLM_PROVIDER: str = "openai"        # openai | anthropic
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str | None = None     # Для self-hosted / proxy

    # ── RAG / Qdrant ─────────────────────────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str | None = None
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ── MQTT ─────────────────────────────────────────────────────────────
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USER: str | None = None
    MQTT_PASSWORD: str | None = None

    # ── WebSocket ────────────────────────────────────────────────────────
    WS_URL: str = "ws://localhost:8080/ws"

    # ── Redis ────────────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    REDIS_KEY_PREFIX: str = ""

    # ── HTTP ─────────────────────────────────────────────────────────────
    HTTP_TIMEOUT: float = 30.0

    # ── Логирование ──────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str | None = None
    LOG_JSON: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
