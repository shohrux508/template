"""
libs.utils.cache — Быстрое хранилище (Redis) с типизированным интерфейсом.

Пример использования:
    cache = CacheService(CacheConfig(host="localhost"))
    await cache.set_val("sensor:1:temp", "22.5", ttl=300)
    value = await cache.get_val("sensor:1:temp")
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field
from loguru import logger


# ── Конфигурация ─────────────────────────────────────────────────────────────


class CacheConfig(BaseModel):
    """Настройки Redis-подключения."""

    host: str = "localhost"
    port: int = Field(default=6379, gt=0, le=65535)
    db: int = Field(default=0, ge=0)
    password: str | None = None
    decode_responses: bool = True
    socket_timeout: float = Field(default=5.0, gt=0)
    max_connections: int = Field(default=10, gt=0)
    key_prefix: str = ""


# ── Сервис ───────────────────────────────────────────────────────────────────


class CacheService:
    """Асинхронный Redis-клиент с типизированным API."""

    def __init__(self, config: CacheConfig | None = None) -> None:
        self.config = config or CacheConfig()
        self._redis: Any = None
        logger.info("CacheService инициализирован (host={}:{})", self.config.host, self.config.port)

    # ── Ленивая инициализация ────────────────────────────────────────────

    async def _get_redis(self) -> Any:
        if self._redis is not None:
            return self._redis

        from redis.asyncio import Redis, ConnectionPool

        pool = ConnectionPool(
            host=self.config.host,
            port=self.config.port,
            db=self.config.db,
            password=self.config.password,
            decode_responses=self.config.decode_responses,
            socket_timeout=self.config.socket_timeout,
            max_connections=self.config.max_connections,
        )
        self._redis = Redis(connection_pool=pool)
        return self._redis

    # ── Приватные хелперы ────────────────────────────────────────────────

    def _key(self, key: str) -> str:
        """Добавить префикс к ключу."""
        if self.config.key_prefix:
            return f"{self.config.key_prefix}:{key}"
        return key

    # ── Публичный API — Строки ───────────────────────────────────────────

    async def get_val(self, key: str) -> str | None:
        """Получить значение по ключу."""
        redis = await self._get_redis()
        value = await redis.get(self._key(key))
        logger.debug("Cache GET {} → {}", key, value is not None)
        return value

    async def set_val(
        self,
        key: str,
        value: str,
        *,
        ttl: int | None = None,
    ) -> None:
        """Установить значение. ttl — время жизни в секундах."""
        redis = await self._get_redis()
        kwargs: dict[str, Any] = {}
        if ttl is not None:
            kwargs["ex"] = ttl
        await redis.set(self._key(key), value, **kwargs)
        logger.debug("Cache SET {} (ttl={})", key, ttl)

    async def delete(self, key: str) -> bool:
        """Удалить ключ. Возвращает True, если ключ существовал."""
        redis = await self._get_redis()
        result = await redis.delete(self._key(key))
        return bool(result)

    async def exists(self, key: str) -> bool:
        """Проверить существование ключа."""
        redis = await self._get_redis()
        return bool(await redis.exists(self._key(key)))

    # ── JSON-объекты ─────────────────────────────────────────────────────

    async def get_json(self, key: str) -> Any:
        """Получить JSON-объект по ключу."""
        value = await self.get_val(key)
        if value is None:
            return None
        return json.loads(value)

    async def set_json(self, key: str, data: Any, *, ttl: int | None = None) -> None:
        """Сохранить объект как JSON."""
        value = json.dumps(data, ensure_ascii=False, default=str)
        await self.set_val(key, value, ttl=ttl)

    # ── Hash ─────────────────────────────────────────────────────────────

    async def hget(self, key: str, field: str) -> str | None:
        """Получить поле из хеша."""
        redis = await self._get_redis()
        return await redis.hget(self._key(key), field)

    async def hset(self, key: str, field: str, value: str) -> None:
        """Установить поле в хеше."""
        redis = await self._get_redis()
        await redis.hset(self._key(key), field, value)

    async def hgetall(self, key: str) -> dict[str, str]:
        """Получить все поля хеша."""
        redis = await self._get_redis()
        return await redis.hgetall(self._key(key))

    # ── Счетчики ─────────────────────────────────────────────────────────

    async def increment(self, key: str, amount: int = 1) -> int:
        """Атомарный инкремент."""
        redis = await self._get_redis()
        return await redis.incrby(self._key(key), amount)

    # ── Списки ───────────────────────────────────────────────────────────

    async def push(self, key: str, *values: str) -> int:
        """Добавить значения в конец списка."""
        redis = await self._get_redis()
        return await redis.rpush(self._key(key), *values)

    async def pop(self, key: str) -> str | None:
        """Достать значение из начала списка."""
        redis = await self._get_redis()
        return await redis.lpop(self._key(key))

    async def list_range(self, key: str, start: int = 0, end: int = -1) -> list[str]:
        """Получить N элементов из списка."""
        redis = await self._get_redis()
        return await redis.lrange(self._key(key), start, end)

    # ── TTL ───────────────────────────────────────────────────────────────

    async def set_ttl(self, key: str, seconds: int) -> bool:
        """Установить TTL на существующий ключ."""
        redis = await self._get_redis()
        return bool(await redis.expire(self._key(key), seconds))

    async def get_ttl(self, key: str) -> int:
        """Получить оставшееся время жизни ключа (-1 = без TTL, -2 = не существует)."""
        redis = await self._get_redis()
        return await redis.ttl(self._key(key))

    # ── Жизненный цикл ──────────────────────────────────────────────────

    async def ping(self) -> bool:
        """Проверить соединение с Redis."""
        try:
            redis = await self._get_redis()
            return await redis.ping()
        except Exception as e:
            logger.error("Cache ping ошибка: {}", e)
            return False

    async def close(self) -> None:
        """Закрыть соединение с Redis."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None
            logger.info("CacheService: соединение закрыто")
