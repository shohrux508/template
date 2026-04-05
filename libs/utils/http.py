"""
libs.utils.http — Асинхронный HTTP-клиент (httpx) с единым интерфейсом.

Пример использования:
    client = HttpClient(HttpConfig(base_url="https://api.example.com"))
    data = await client.get_json("/users")
    await client.close()
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from loguru import logger


# ── Конфигурация ─────────────────────────────────────────────────────────────


class HttpConfig(BaseModel):
    """Настройки HTTP-клиента."""

    base_url: str = ""
    timeout: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=3, ge=0)
    headers: dict[str, str] = Field(default_factory=dict)
    follow_redirects: bool = True
    verify_ssl: bool = True


# ── Сервис ───────────────────────────────────────────────────────────────────


class HttpClient:
    """Единый асинхронный HTTP-клиент на базе httpx."""

    def __init__(self, config: HttpConfig | None = None) -> None:
        self.config = config or HttpConfig()
        self._client: Any = None
        logger.info("HttpClient инициализирован (base_url='{}')", self.config.base_url)

    # ── Ленивая инициализация ────────────────────────────────────────────

    async def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        import httpx

        transport = httpx.AsyncHTTPTransport(retries=self.config.max_retries)
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout,
            headers=self.config.headers,
            follow_redirects=self.config.follow_redirects,
            verify=self.config.verify_ssl,
            transport=transport,
        )
        return self._client

    # ── Публичный API ────────────────────────────────────────────────────

    async def get(self, url: str, **kwargs: Any) -> Any:
        """GET-запрос, вернуть Response."""
        client = await self._get_client()
        response = await client.get(url, **kwargs)
        response.raise_for_status()
        logger.debug("HTTP GET {} → {}", url, response.status_code)
        return response

    async def get_json(self, url: str, **kwargs: Any) -> Any:
        """GET-запрос, вернуть JSON."""
        response = await self.get(url, **kwargs)
        return response.json()

    async def get_text(self, url: str, **kwargs: Any) -> str:
        """GET-запрос, вернуть текст."""
        response = await self.get(url, **kwargs)
        return response.text

    async def post(self, url: str, **kwargs: Any) -> Any:
        """POST-запрос."""
        client = await self._get_client()
        response = await client.post(url, **kwargs)
        response.raise_for_status()
        logger.debug("HTTP POST {} → {}", url, response.status_code)
        return response

    async def post_json(self, url: str, data: Any, **kwargs: Any) -> Any:
        """POST-запрос с JSON-телом, вернуть JSON."""
        response = await self.post(url, json=data, **kwargs)
        return response.json()

    async def put(self, url: str, **kwargs: Any) -> Any:
        """PUT-запрос."""
        client = await self._get_client()
        response = await client.put(url, **kwargs)
        response.raise_for_status()
        logger.debug("HTTP PUT {} → {}", url, response.status_code)
        return response

    async def delete(self, url: str, **kwargs: Any) -> Any:
        """DELETE-запрос."""
        client = await self._get_client()
        response = await client.delete(url, **kwargs)
        response.raise_for_status()
        logger.debug("HTTP DELETE {} → {}", url, response.status_code)
        return response

    async def download(self, url: str, path: str, **kwargs: Any) -> str:
        """Скачать файл и сохранить на диск."""
        client = await self._get_client()
        async with client.stream("GET", url, **kwargs) as response:
            response.raise_for_status()
            with open(path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
        logger.info("HTTP: скачан {} → {}", url, path)
        return path

    # ── Жизненный цикл ──────────────────────────────────────────────────

    async def close(self) -> None:
        """Закрыть HTTP-клиент."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("HttpClient: закрыт")
