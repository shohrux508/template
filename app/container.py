"""
app.container — DI-контейнер с поддержкой ленивой инициализации.

Поддерживает два режима:
  - register(name, instance)        — немедленная регистрация (лёгкие объекты)
  - register_lazy(name, factory)    — объект создаётся при ПЕРВОМ обращении

Typed property accessors для libs/ также используют ленивый путь.
"""

from __future__ import annotations

from typing import Any, Callable


class Container:
    """Service-locator с ленивой инициализацией тяжёлых зависимостей."""

    def __init__(self) -> None:
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Callable[[], Any]] = {}

    # ── Универсальный реестр ─────────────────────────────────────────────

    def register(self, name: str, instance: Any) -> None:
        """Зарегистрировать готовый экземпляр (лёгкие объекты)."""
        if name in self._services or name in self._factories:
            raise ValueError(f"Сервис '{name}' уже зарегистрирован")
        self._services[name] = instance

    def register_lazy(self, name: str, factory: Callable[[], Any]) -> None:
        """Зарегистрировать фабрику — объект будет создан при первом вызове get().

        Подходит для тяжёлых модулей: Playwright, Pandas-обёрток, и т.д.
        Ленивая инициализация экономит память и ускоряет старт приложения.
        """
        if name in self._services or name in self._factories:
            raise ValueError(f"Сервис '{name}' уже зарегистрирован")
        self._factories[name] = factory

    def get(self, name: str) -> Any:
        """Получить сервис по имени. Если зарегистрирован лениво — создаст при первом вызове."""
        # Уже создан?
        if name in self._services:
            return self._services[name]

        # Есть фабрика? Создаём, кешируем, удаляем фабрику.
        if name in self._factories:
            instance = self._factories.pop(name)()
            self._services[name] = instance
            return instance

        raise ValueError(f"Сервис '{name}' не найден")

    def has(self, name: str) -> bool:
        """Проверить, зарегистрирован ли сервис (включая ленивые)."""
        return name in self._services or name in self._factories

    def is_initialized(self, name: str) -> bool:
        """Проверить, был ли ленивый сервис уже инициализирован."""
        return name in self._services

    # ── Typed accessors для libs/ ────────────────────────────────────────

    @property
    def llm(self) -> Any:
        """libs.ai.engine.LLMEngine"""
        return self.get("llm")

    @property
    def rag(self) -> Any:
        """libs.ai.rag.RAGService"""
        return self.get("rag")

    @property
    def mqtt(self) -> Any:
        """libs.iot.mqtt.MQTTService"""
        return self.get("mqtt")

    @property
    def ws(self) -> Any:
        """libs.iot.ws_client.WSClient"""
        return self.get("ws")

    @property
    def http(self) -> Any:
        """libs.utils.http.HttpClient"""
        return self.get("http")

    @property
    def cache(self) -> Any:
        """libs.utils.cache.CacheService"""
        return self.get("cache")

    @property
    def scheduler(self) -> Any:
        """libs.utils.scheduler.SchedulerService"""
        return self.get("scheduler")

    @property
    def console(self) -> Any:
        """libs.ui.console.Console"""
        return self.get("console")

    @property
    def analysis(self) -> Any:
        """libs.data.analysis.AnalysisService"""
        return self.get("analysis")

    @property
    def viz(self) -> Any:
        """libs.data.viz.VizService"""
        return self.get("viz")

    @property
    def browser(self) -> Any:
        """libs.crawler.browser.BrowserService"""
        return self.get("browser")

    @property
    def parser(self) -> Any:
        """libs.crawler.parser.ParserService"""
        return self.get("parser")
