"""
libs.iot.mqtt — Обертка MQTT-клиента (aiomqtt) с автоматическим реконнектом.

Пример использования:
    mqtt = MQTTService(MQTTConfig(host="192.168.1.100"))
    await mqtt.publish("home/light", "on")
    async for topic, payload in mqtt.subscribe("sensors/#"):
        print(topic, payload)
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field
from loguru import logger


# ── Конфигурация ─────────────────────────────────────────────────────────────


class MQTTConfig(BaseModel):
    """Настройки MQTT-подключения."""

    host: str = "localhost"
    port: int = Field(default=1883, gt=0, le=65535)
    username: str | None = None
    password: str | None = None
    client_id: str | None = None
    keepalive: int = Field(default=60, gt=0)
    reconnect_interval: float = Field(default=5.0, gt=0)
    max_reconnect_attempts: int = Field(default=0, ge=0)  # 0 = бесконечно


# ── Модели данных ────────────────────────────────────────────────────────────


class MQTTMessage(BaseModel):
    """Входящее MQTT-сообщение."""

    topic: str
    payload: str
    qos: int = 0
    retain: bool = False


# ── Сервис ───────────────────────────────────────────────────────────────────


class MQTTService:
    """Асинхронный MQTT-клиент с автоматическим реконнектом."""

    def __init__(self, config: MQTTConfig) -> None:
        self.config = config
        self._handlers: dict[str, list[Callable[[MQTTMessage], Awaitable[None]]]] = {}
        self._running: bool = False
        logger.info("MQTTService инициализирован (host={}:{})", config.host, config.port)

    # ── Публичный API ────────────────────────────────────────────────────

    async def publish(self, topic: str, payload: str, *, qos: int = 0) -> None:
        """Отправить сообщение в топик."""
        from aiomqtt import Client

        try:
            async with self._create_client() as client:
                await client.publish(topic, payload=payload, qos=qos)
                logger.info("MQTT → {} : {}", topic, payload[:100])
        except Exception as e:
            logger.error("MQTT publish ошибка: {}", e)
            raise

    async def subscribe(self, topic: str) -> AsyncIterator[MQTTMessage]:
        """Подписаться на топик и получать сообщения (async generator)."""
        from aiomqtt import Client, MqttError

        attempt = 0
        while True:
            try:
                async with self._create_client() as client:
                    await client.subscribe(topic)
                    logger.info("MQTT ← подписка на '{}'", topic)
                    attempt = 0  # Сброс счетчика при успешном подключении

                    async for message in client.messages:
                        yield MQTTMessage(
                            topic=str(message.topic),
                            payload=message.payload.decode()
                            if isinstance(message.payload, bytes)
                            else str(message.payload),
                        )
            except MqttError as e:
                attempt += 1
                max_att = self.config.max_reconnect_attempts
                if max_att > 0 and attempt >= max_att:
                    logger.error("MQTT: превышено кол-во попыток реконнекта ({})", max_att)
                    raise

                logger.warning(
                    "MQTT: потеря связи ({}), реконнект через {}с (попытка {})",
                    e,
                    self.config.reconnect_interval,
                    attempt,
                )
                await asyncio.sleep(self.config.reconnect_interval)

    def on_message(self, topic: str):
        """Декоратор для регистрации обработчика на определенный топик."""

        def decorator(func: Callable[[MQTTMessage], Awaitable[None]]):
            if topic not in self._handlers:
                self._handlers[topic] = []
            self._handlers[topic].append(func)
            return func

        return decorator

    async def listen(self) -> None:
        """Запустить прослушивание всех зарегистрированных топиков."""
        if not self._handlers:
            logger.warning("MQTT listen: нет зарегистрированных обработчиков")
            return

        self._running = True
        topics = list(self._handlers.keys())

        # Подписываемся на все топики через один клиент
        from aiomqtt import Client, MqttError
        import asyncio as _asyncio

        attempt = 0
        while self._running:
            try:
                async with self._create_client() as client:
                    for t in topics:
                        await client.subscribe(t)
                    logger.info("MQTT listen: подписка на {}", topics)
                    attempt = 0

                    async for message in client.messages:
                        msg = MQTTMessage(
                            topic=str(message.topic),
                            payload=message.payload.decode()
                            if isinstance(message.payload, bytes)
                            else str(message.payload),
                        )
                        # Вызываем подходящие обработчики
                        for pattern, handlers in self._handlers.items():
                            if self._topic_matches(pattern, msg.topic):
                                for handler in handlers:
                                    try:
                                        await handler(msg)
                                    except Exception as e:
                                        logger.error(
                                            "MQTT handler ошибка (topic={}): {}",
                                            msg.topic,
                                            e,
                                        )
            except MqttError as e:
                attempt += 1
                max_att = self.config.max_reconnect_attempts
                if max_att > 0 and attempt >= max_att:
                    logger.error("MQTT listen: превышен лимит реконнектов")
                    raise
                logger.warning("MQTT listen: реконнект через {}с", self.config.reconnect_interval)
                await _asyncio.sleep(self.config.reconnect_interval)

    def stop(self) -> None:
        """Остановить прослушивание."""
        self._running = False
        logger.info("MQTT listen: остановлен")

    # ── Приватные методы ─────────────────────────────────────────────────

    def _create_client(self) -> Any:
        from aiomqtt import Client

        kwargs: dict[str, Any] = {
            "hostname": self.config.host,
            "port": self.config.port,
            "keepalive": self.config.keepalive,
        }
        if self.config.username:
            kwargs["username"] = self.config.username
        if self.config.password:
            kwargs["password"] = self.config.password
        if self.config.client_id:
            kwargs["identifier"] = self.config.client_id

        return Client(**kwargs)

    @staticmethod
    def _topic_matches(pattern: str, topic: str) -> bool:
        """Простое сопоставление MQTT-топиков (поддержка # и +)."""
        pattern_parts = pattern.split("/")
        topic_parts = topic.split("/")

        for i, p in enumerate(pattern_parts):
            if p == "#":
                return True
            if i >= len(topic_parts):
                return False
            if p != "+" and p != topic_parts[i]:
                return False

        return len(pattern_parts) == len(topic_parts)
