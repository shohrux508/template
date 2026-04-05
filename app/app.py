"""
app.app — Orchestrator: сборка, инициализация и запуск всех компонентов.
"""

import asyncio

from loguru import logger

from app.config import settings
from app.container import Container
from app.services.example_service import ExampleService


class App:
    def __init__(self) -> None:
        self.container = Container()

    # ── Настройка логирования ────────────────────────────────────────────

    def setup_logging(self) -> None:
        from libs.utils.logger import setup_logger

        setup_logger(
            level=settings.LOG_LEVEL,
            log_file=settings.LOG_FILE,
            json_output=settings.LOG_JSON,
        )

    # ── Регистрация библиотечных сервисов (libs/) ────────────────────────

    def setup_libs(self) -> None:
        """Plug-and-Play инициализация инженерного слоя.

        Каждый модуль создается одной строчкой и сразу готов к работе.
        Если модуль не нужен — просто закомментируйте строку.
        """

        # ── AI ────────────────────────────────────────────────────────
        from libs.ai.engine import LLMEngine, LLMConfig

        self.container.register("llm", LLMEngine(LLMConfig(
            provider=settings.LLM_PROVIDER,  # type: ignore[arg-type]
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL,
        )))

        from libs.ai.rag import RAGService, RAGConfig

        self.container.register("rag", RAGService(RAGConfig(
            qdrant_url=settings.QDRANT_URL,
            qdrant_api_key=settings.QDRANT_API_KEY,
            embedding_api_key=settings.EMBEDDING_API_KEY,
            embedding_model=settings.EMBEDDING_MODEL,
        )))

        # ── IoT ───────────────────────────────────────────────────────
        from libs.iot.mqtt import MQTTService, MQTTConfig

        self.container.register("mqtt", MQTTService(MQTTConfig(
            host=settings.MQTT_HOST,
            port=settings.MQTT_PORT,
            username=settings.MQTT_USER,
            password=settings.MQTT_PASSWORD,
        )))

        from libs.iot.ws_client import WSClient, WSConfig

        self.container.register("ws", WSClient(WSConfig(
            url=settings.WS_URL,
        )))

        # ── Data ──────────────────────────────────────────────────────
        from libs.data.analysis import AnalysisService

        self.container.register("analysis", AnalysisService())

        from libs.data.viz import VizService

        self.container.register("viz", VizService())

        # ── Crawler ───────────────────────────────────────────────────
        from libs.crawler.browser import BrowserService

        self.container.register("browser", BrowserService())

        from libs.crawler.parser import ParserService

        self.container.register("parser", ParserService())

        # ── UI ────────────────────────────────────────────────────────
        from libs.ui.console import Console

        self.container.register("console", Console())

        # ── Utils ─────────────────────────────────────────────────────
        from libs.utils.http import HttpClient, HttpConfig

        self.container.register("http", HttpClient(HttpConfig(
            timeout=settings.HTTP_TIMEOUT,
        )))

        from libs.utils.scheduler import SchedulerService

        self.container.register("scheduler", SchedulerService())

        from libs.utils.cache import CacheService, CacheConfig

        self.container.register("cache", CacheService(CacheConfig(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            key_prefix=settings.REDIS_KEY_PREFIX,
        )))

        logger.info("libs/ — все модули зарегистрированы в контейнере")

    # ── Регистрация бизнес-сервисов ──────────────────────────────────────

    def setup_services(self) -> None:
        logger.info("Настройка бизнес-сервисов…")
        self.container.register("example_service", ExampleService())

    # ── Запуск подсистем ─────────────────────────────────────────────────

    async def setup_telegram(self):
        if settings.RUN_TELEGRAM:
            from app.telegram.bot import start_telegram

            logger.info("Запуск Telegram Bot…")
            return start_telegram(self.container)
        return None

    async def setup_api(self):
        if settings.RUN_API:
            from app.api.server import start_api

            logger.info("Запуск API Server…")
            return start_api(self.container)
        return None

    # ── Главный цикл ─────────────────────────────────────────────────────

    async def run(self) -> None:
        self.setup_logging()
        self.setup_libs()
        self.setup_services()

        tasks = []

        telegram_task = await self.setup_telegram()
        if telegram_task:
            tasks.append(telegram_task)

        api_task = await self.setup_api()
        if api_task:
            tasks.append(api_task)

        if not tasks:
            logger.warning("Ни один компонент не включен (RUN_TELEGRAM=False, RUN_API=False)")
            return

        try:
            await asyncio.gather(*tasks)
        finally:
            await self._shutdown()

    async def _shutdown(self) -> None:
        """Корректное завершение всех ресурсов."""
        logger.info("Завершение работы…")

        for name in ("llm", "rag", "http", "cache", "ws"):
            if self.container.has(name):
                svc = self.container.get(name)
                if hasattr(svc, "close"):
                    try:
                        await svc.close()
                    except Exception as e:
                        logger.warning("Ошибка при закрытии {}: {}", name, e)

        if self.container.has("scheduler"):
            try:
                await self.container.scheduler.shutdown()
            except Exception as e:
                logger.warning("Ошибка при остановке scheduler: {}", e)

        logger.info("Все ресурсы освобождены")
