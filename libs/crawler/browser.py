"""
libs.crawler.browser — Автоматизация браузера (Playwright).

Пример использования:
    browser = BrowserService(BrowserConfig(headless=True))
    async with browser:
        html = await browser.get_page_content("https://example.com")
        await browser.screenshot("https://example.com", "shot.png")
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from loguru import logger


# ── Конфигурация ─────────────────────────────────────────────────────────────


class BrowserConfig(BaseModel):
    """Настройки Playwright-браузера."""

    headless: bool = True
    browser_type: str = "chromium"  # chromium, firefox, webkit
    timeout: int = Field(default=30000, gt=0)  # мс
    user_agent: str | None = None
    viewport_width: int = Field(default=1920, gt=0)
    viewport_height: int = Field(default=1080, gt=0)
    proxy: str | None = None


# ── Сервис ───────────────────────────────────────────────────────────────────


class BrowserService:
    """Обертка Playwright для скрейпинга и автоматизации."""

    def __init__(self, config: BrowserConfig | None = None) -> None:
        self.config = config or BrowserConfig()
        self._playwright: Any = None
        self._browser: Any = None
        logger.info("BrowserService инициализирован (headless={})", self.config.headless)

    # ── Context Manager ──────────────────────────────────────────────────

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # ── Жизненный цикл ──────────────────────────────────────────────────

    async def start(self) -> None:
        """Запустить Playwright и браузер."""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()

        launcher = getattr(self._playwright, self.config.browser_type)
        launch_kwargs: dict[str, Any] = {"headless": self.config.headless}
        if self.config.proxy:
            launch_kwargs["proxy"] = {"server": self.config.proxy}

        self._browser = await launcher.launch(**launch_kwargs)
        logger.info("BrowserService: {} запущен", self.config.browser_type)

    async def close(self) -> None:
        """Закрыть браузер и Playwright."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._playwright = None
        logger.info("BrowserService: закрыт")

    # ── Создание контекста / страницы ────────────────────────────────────

    async def _new_page(self) -> Any:
        """Создать новую страницу с настроенным контекстом."""
        if not self._browser:
            raise RuntimeError("BrowserService не запущен. Используйте async with или start()")

        context_kwargs: dict[str, Any] = {
            "viewport": {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            },
        }
        if self.config.user_agent:
            context_kwargs["user_agent"] = self.config.user_agent

        context = await self._browser.new_context(**context_kwargs)
        page = await context.new_page()
        page.set_default_timeout(self.config.timeout)
        return page

    # ── Публичный API ────────────────────────────────────────────────────

    async def get_page_content(self, url: str) -> str:
        """Загрузить страницу и вернуть полный HTML."""
        page = await self._new_page()
        try:
            await page.goto(url, wait_until="networkidle")
            content = await page.content()
            logger.info("Browser: загружена страница {} ({} символов)", url, len(content))
            return content
        finally:
            await page.context.close()

    async def get_text(self, url: str) -> str:
        """Загрузить страницу и вернуть только текст."""
        page = await self._new_page()
        try:
            await page.goto(url, wait_until="networkidle")
            text = await page.inner_text("body")
            logger.info("Browser: текст страницы {} ({} символов)", url, len(text))
            return text
        finally:
            await page.context.close()

    async def screenshot(self, url: str, path: str, *, full_page: bool = True) -> str:
        """Сделать скриншот страницы и сохранить в файл."""
        page = await self._new_page()
        try:
            await page.goto(url, wait_until="networkidle")
            await page.screenshot(path=path, full_page=full_page)
            logger.info("Browser: скриншот → {}", path)
            return path
        finally:
            await page.context.close()

    async def evaluate(self, url: str, script: str) -> Any:
        """Выполнить JavaScript на странице и вернуть результат."""
        page = await self._new_page()
        try:
            await page.goto(url, wait_until="networkidle")
            result = await page.evaluate(script)
            return result
        finally:
            await page.context.close()

    async def click_and_wait(
        self,
        url: str,
        selector: str,
        *,
        wait_for: str = "networkidle",
    ) -> str:
        """Перейти на страницу, кликнуть по элементу и вернуть итоговый HTML."""
        page = await self._new_page()
        try:
            await page.goto(url, wait_until="networkidle")
            await page.click(selector)
            await page.wait_for_load_state(wait_for)
            content = await page.content()
            logger.info("Browser: click_and_wait '{}' на {}", selector, url)
            return content
        finally:
            await page.context.close()
