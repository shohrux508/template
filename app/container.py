"""
app.container — Простой DI-контейнер / реестр сервисов.

Поддерживает строгую типизацию при получении библиотечных сервисов
через именованные property, а также произвольные пользовательские
сервисы через .register() / .get().
"""

from __future__ import annotations

from typing import Any


class Container:
    """Service-locator для всех зависимостей приложения."""

    def __init__(self) -> None:
        self._services: dict[str, Any] = {}

    # ── Универсальный реестр ─────────────────────────────────────────────

    def register(self, name: str, instance: Any) -> None:
        """Зарегистрировать сервис по имени. Повторная регистрация = ошибка."""
        if name in self._services:
            raise ValueError(f"Сервис '{name}' уже зарегистрирован")
        self._services[name] = instance

    def get(self, name: str) -> Any:
        """Получить сервис по имени."""
        if name not in self._services:
            raise ValueError(f"Сервис '{name}' не найден")
        return self._services[name]

    def has(self, name: str) -> bool:
        """Проверить, зарегистрирован ли сервис."""
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
