"""
libs.iot.ws_client — Чистый WebSocket-клиент с автоматическим реконнектом.

Пример использования:
    ws = WSClient(WSConfig(url="ws://192.168.1.100:81/ws"))
    async for message in ws.listen():
        print(message)
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field
from loguru import logger


# ── Конфигурация ─────────────────────────────────────────────────────────────


class WSConfig(BaseModel):
    """Настройки WebSocket-подключения."""

    url: str = "ws://localhost:8080/ws"
    reconnect_interval: float = Field(default=3.0, gt=0)
    max_reconnect_attempts: int = Field(default=0, ge=0)  # 0 = бесконечно
    ping_interval: float | None = Field(default=20.0, gt=0)
    ping_timeout: float | None = Field(default=20.0, gt=0)
    extra_headers: dict[str, str] = Field(default_factory=dict)


# ── Сервис ───────────────────────────────────────────────────────────────────


class WSClient:
    """Низкоуровневый асинхронный WebSocket-клиент с автореконнектом."""

    def __init__(self, config: WSConfig) -> None:
        self.config = config
        self._ws: Any = None
        self._running: bool = False
        self._on_message: Callable[[str], Awaitable[None]] | None = None
        self._on_connect: Callable[[], Awaitable[None]] | None = None
        self._on_disconnect: Callable[[], Awaitable[None]] | None = None
        logger.info("WSClient инициализирован (url={})", config.url)

    # ── Публичный API ────────────────────────────────────────────────────

    async def send(self, message: str) -> None:
        """Отправить сообщение через текущее соединение."""
        if self._ws is None:
            raise ConnectionError("WebSocket не подключен")
        try:
            await self._ws.send(message)
            logger.debug("WS → {}", message[:200])
        except Exception as e:
            logger.error("WS send ошибка: {}", e)
            raise

    async def listen(self) -> AsyncIterator[str]:
        """Подключиться и получать сообщения (async generator с реконнектом)."""
        import websockets

        attempt = 0
        self._running = True

        while self._running:
            try:
                extra: dict[str, Any] = {}
                if self.config.ping_interval is not None:
                    extra["ping_interval"] = self.config.ping_interval
                if self.config.ping_timeout is not None:
                    extra["ping_timeout"] = self.config.ping_timeout
                if self.config.extra_headers:
                    extra["additional_headers"] = self.config.extra_headers

                async with websockets.connect(self.config.url, **extra) as ws:
                    self._ws = ws
                    attempt = 0
                    logger.info("WS: подключен к {}", self.config.url)

                    if self._on_connect:
                        await self._on_connect()

                    async for raw in ws:
                        message = raw if isinstance(raw, str) else raw.decode()
                        yield message

            except Exception as e:
                self._ws = None

                if self._on_disconnect:
                    try:
                        await self._on_disconnect()
                    except Exception:
                        pass

                attempt += 1
                max_att = self.config.max_reconnect_attempts
                if max_att > 0 and attempt >= max_att:
                    logger.error("WS: превышен лимит реконнектов ({})", max_att)
                    raise

                logger.warning(
                    "WS: потеря связи ({}), реконнект через {}с (попытка {})",
                    e,
                    self.config.reconnect_interval,
                    attempt,
                )
                await asyncio.sleep(self.config.reconnect_interval)

        self._ws = None

    async def connect_and_run(
        self,
        on_message: Callable[[str], Awaitable[None]],
        *,
        on_connect: Callable[[], Awaitable[None]] | None = None,
        on_disconnect: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        """Альтернативный API — запуск с callback-ами."""
        self._on_message = on_message
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect

        async for message in self.listen():
            if self._on_message:
                try:
                    await self._on_message(message)
                except Exception as e:
                    logger.error("WS handler ошибка: {}", e)

    def stop(self) -> None:
        """Остановить клиент."""
        self._running = False
        logger.info("WSClient: остановлен")

    # ── Жизненный цикл ──────────────────────────────────────────────────

    async def close(self) -> None:
        """Закрыть WebSocket-соединение."""
        self.stop()
        if self._ws:
            await self._ws.close()
            self._ws = None
        logger.info("WSClient: соединение закрыто")
