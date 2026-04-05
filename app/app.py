"""
app.app — Orchestrator: сборка, инициализация и запуск всех компонентов.

Порядок завершения (graceful shutdown):
  1. Остановить приём новых задач (FastAPI / Telegram polling)
  2. Корректно закрыть сетевые сессии (MQTT, WebSocket, HTTP, Redis)
  3. Остановить планировщик
  4. Записать финальные логи
"""

from __future__ import annotations

import asyncio
import signal
import sys

from loguru import logger

from app.config import settings
from app.container import Container
from app.services.example_service import ExampleService


class App:
    def __init__(self) -> None:
        self.container = Container()
        self._shutdown_event = asyncio.Event()

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
        """Plug-and-Play: ленивая регистрация инженерного слоя.

        Тяжёлые модули (Playwright, Pandas, Rich) создаются ТОЛЬКО
        при первом обращении через container.get() / container.property.
        Это экономит память и ускоряет старт приложения.

        Если модуль не нужен — просто закомментируйте строку.
        """

        # ── AI ────────────────────────────────────────────────────────
        self.container.register_lazy("llm", lambda: self._make_llm())
        self.container.register_lazy("rag", lambda: self._make_rag())

        # ── IoT ───────────────────────────────────────────────────────
        self.container.register_lazy("mqtt", lambda: self._make_mqtt())
        self.container.register_lazy("ws", lambda: self._make_ws())

        # ── Data ──────────────────────────────────────────────────────
        self.container.register_lazy("analysis", lambda: self._make_analysis())
        self.container.register_lazy("viz", lambda: self._make_viz())

        # ── Crawler ───────────────────────────────────────────────────
        self.container.register_lazy("browser", lambda: self._make_browser())
        self.container.register_lazy("parser", lambda: self._make_parser())

        # ── UI ────────────────────────────────────────────────────────
        self.container.register_lazy("console", lambda: self._make_console())

        # ── Utils ─────────────────────────────────────────────────────
        self.container.register_lazy("http", lambda: self._make_http())
        self.container.register_lazy("scheduler", lambda: self._make_scheduler())
        self.container.register_lazy("cache", lambda: self._make_cache())

        logger.info("libs/ — все модули зарегистрированы (lazy)")

    # ── Фабрики (вызываются ТОЛЬКО при первом обращении) ─────────────────

    @staticmethod
    def _make_llm():
        from libs.ai.engine import LLMEngine, LLMConfig
        return LLMEngine(LLMConfig(
            provider=settings.LLM_PROVIDER,  # type: ignore[arg-type]
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL,
        ))

    @staticmethod
    def _make_rag():
        from libs.ai.rag import RAGService, RAGConfig
        return RAGService(RAGConfig(
            qdrant_url=settings.QDRANT_URL,
            qdrant_api_key=settings.QDRANT_API_KEY,
            embedding_api_key=settings.EMBEDDING_API_KEY,
            embedding_model=settings.EMBEDDING_MODEL,
        ))

    @staticmethod
    def _make_mqtt():
        from libs.iot.mqtt import MQTTService, MQTTConfig
        return MQTTService(MQTTConfig(
            host=settings.MQTT_HOST,
            port=settings.MQTT_PORT,
            username=settings.MQTT_USER,
            password=settings.MQTT_PASSWORD,
        ))

    @staticmethod
    def _make_ws():
        from libs.iot.ws_client import WSClient, WSConfig
        return WSClient(WSConfig(url=settings.WS_URL))

    @staticmethod
    def _make_analysis():
        from libs.data.analysis import AnalysisService
        return AnalysisService()

    @staticmethod
    def _make_viz():
        from libs.data.viz import VizService
        return VizService()

    @staticmethod
    def _make_browser():
        from libs.crawler.browser import BrowserService
        return BrowserService()

    @staticmethod
    def _make_parser():
        from libs.crawler.parser import ParserService
        return ParserService()

    @staticmethod
    def _make_console():
        from libs.ui.console import Console
        return Console()

    @staticmethod
    def _make_http():
        from libs.utils.http import HttpClient, HttpConfig
        return HttpClient(HttpConfig(timeout=settings.HTTP_TIMEOUT))

    @staticmethod
    def _make_scheduler():
        from libs.utils.scheduler import SchedulerService
        return SchedulerService()

    @staticmethod
    def _make_cache():
        from libs.utils.cache import CacheService, CacheConfig
        return CacheService(CacheConfig(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            key_prefix=settings.REDIS_KEY_PREFIX,
        ))

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

    # ── Обработка сигналов завершения ────────────────────────────────────

    def _install_signal_handlers(self, loop: asyncio.AbstractEventLoop) -> None:
        """Установить обработчики SIGINT / SIGTERM для graceful shutdown."""
        def _signal_handler(sig_name: str):
            logger.info("Получен сигнал {}, начинаю graceful shutdown…", sig_name)
            self._shutdown_event.set()

        # На Windows signal.signal() работает, но add_signal_handler — нет
        if sys.platform != "win32":
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, _signal_handler, sig.name)
        # На Windows KeyboardInterrupt ловится в main.py

    # ── Главный цикл ─────────────────────────────────────────────────────

    async def run(self) -> None:
        self.setup_logging()
        self.setup_libs()
        self.setup_services()

        loop = asyncio.get_running_loop()
        self._install_signal_handlers(loop)

        tasks: list[asyncio.Task] = []

        telegram_coro = await self.setup_telegram()
        if telegram_coro:
            tasks.append(asyncio.create_task(telegram_coro, name="telegram"))

        api_coro = await self.setup_api()
        if api_coro:
            tasks.append(asyncio.create_task(api_coro, name="api"))

        if not tasks:
            logger.warning("Ни один компонент не включен (RUN_TELEGRAM=False, RUN_API=False)")
            return

        # Ждём завершения задач ИЛИ сигнала shutdown
        shutdown_task = asyncio.create_task(
            self._shutdown_event.wait(), name="shutdown_watcher"
        )

        try:
            done, pending = await asyncio.wait(
                [*tasks, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Если сработал shutdown_event — отменяем рабочие задачи
            if shutdown_task in done:
                logger.info("Shutdown event: отменяю рабочие задачи…")
                for t in tasks:
                    t.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            shutdown_task.cancel()
            await self._shutdown()

    # ── Graceful Shutdown (упорядоченный) ─────────────────────────────────

    async def _shutdown(self) -> None:
        """Корректное завершение всех ресурсов в правильном порядке:

        1. Остановить приём новых задач (уже сделано через cancel)
        2. Закрыть сетевые сессии (MQTT, WS, HTTP, Redis)
        3. Остановить планировщик
        4. Финальные логи
        """
        logger.info("── Graceful Shutdown ──────────────────────────────")

        # Фаза 1: Остановить IoT-соединения (mqtt.stop, ws.stop)
        for name in ("mqtt", "ws"):
            if self.container.is_initialized(name):
                svc = self.container.get(name)
                if hasattr(svc, "stop"):
                    try:
                        svc.stop()
                        logger.debug("  ✓ {} остановлен", name)
                    except Exception as e:
                        logger.warning("  ✗ Ошибка при остановке {}: {}", name, e)

        # Фаза 2: Закрыть сетевые клиенты (async close)
        for name in ("llm", "rag", "http", "cache", "ws"):
            if self.container.is_initialized(name):
                svc = self.container.get(name)
                if hasattr(svc, "close"):
                    try:
                        await svc.close()
                        logger.debug("  ✓ {} закрыт", name)
                    except Exception as e:
                        logger.warning("  ✗ Ошибка при закрытии {}: {}", name, e)

        # Фаза 3: Остановить планировщик
        if self.container.is_initialized("scheduler"):
            try:
                await self.container.scheduler.shutdown(wait=False)
                logger.debug("  ✓ scheduler остановлен")
            except Exception as e:
                logger.warning("  ✗ Ошибка при остановке scheduler: {}", e)

        # Фаза 4: Финальные логи
        logger.info("── Все ресурсы освобождены ────────────────────────")
