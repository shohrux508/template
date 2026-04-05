"""
libs.ai.engine — Унифицированный интерфейс к LLM (OpenAI / Anthropic).

Пример использования:
    engine = LLMEngine(LLMConfig(provider="openai", api_key="sk-..."))
    answer = await engine.ask("Столица Франции?")
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from loguru import logger


# ── Конфигурация ─────────────────────────────────────────────────────────────


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class LLMConfig(BaseModel):
    """Настройки LLM-движка, получаемые из app.config."""

    provider: LLMProvider = LLMProvider.OPENAI
    api_key: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)
    base_url: str | None = None  # Для self-hosted / proxy


# ── Сервис ───────────────────────────────────────────────────────────────────


class LLMEngine:
    """Обертка для работы с LLM-провайдерами через единый интерфейс."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._client: Any = None
        logger.info("LLMEngine инициализирован (provider={})", config.provider.value)

    # ── Ленивая инициализация клиента ────────────────────────────────────

    async def _get_client(self) -> Any:
        """Ленивое создание клиента — импорт происходит только при первом вызове."""
        if self._client is not None:
            return self._client

        if self.config.provider == LLMProvider.OPENAI:
            from openai import AsyncOpenAI

            kwargs: dict[str, Any] = {"api_key": self.config.api_key}
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            self._client = AsyncOpenAI(**kwargs)

        elif self.config.provider == LLMProvider.GEMINI:
            import google.generativeai as genai

            genai.configure(api_key=self.config.api_key)
            self._client = genai.GenerativeModel(model_name=self.config.model)

        return self._client

    # ── Публичный API ────────────────────────────────────────────────────

    async def ask(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Отправить простой запрос и получить текстовый ответ."""
        client = await self._get_client()
        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        try:
            if self.config.provider == LLMProvider.OPENAI:
                return await self._ask_openai(client, prompt, system, temp, tokens)
            elif self.config.provider == LLMProvider.ANTHROPIC:
                return await self._ask_anthropic(client, prompt, system, temp, tokens)
            elif self.config.provider == LLMProvider.GEMINI:
                return await self._ask_gemini(client, prompt, system, temp, tokens)
            else:
                raise ValueError(f"Неизвестный провайдер: {self.config.provider}")
        except Exception as e:
            logger.error("LLMEngine.ask ошибка: {}", e)
            raise

    async def ask_stream(
        self,
        prompt: str,
        *,
        system: str | None = None,
    ):
        """Стриминговый ответ (async generator, yield-ит чанки текста)."""
        client = await self._get_client()

        try:
            if self.config.provider == LLMProvider.OPENAI:
                messages: list[dict[str, str]] = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})

                stream = await client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    stream=True,
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta

            elif self.config.provider == LLMProvider.ANTHROPIC:
                sys_param = system or ""
                async with client.messages.stream(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    system=sys_param,
                    messages=[{"role": "user", "content": prompt}],
                ) as stream:
                    async for text in stream.text_stream:
                        yield text

            elif self.config.provider == LLMProvider.GEMINI:
                from google.generativeai.types import GenerationConfig

                # Если передан системный промпт, нужно пересоздать модель с ним
                model = client
                if system:
                    import google.generativeai as genai

                    model = genai.GenerativeModel(
                        model_name=self.config.model,
                        system_instruction=system,
                    )

                gen_config = GenerationConfig(
                    temperature=self.config.temperature,
                    max_output_tokens=self.config.max_tokens,
                )

                stream = await model.generate_content_async(
                    prompt,
                    generation_config=gen_config,
                    stream=True,
                )
                async for chunk in stream:
                    if chunk.text:
                        yield chunk.text
        except Exception as e:
            logger.error("LLMEngine.ask_stream ошибка: {}", e)
            raise

    # ── Приватные методы ─────────────────────────────────────────────────

    async def _ask_openai(
        self,
        client: Any,
        prompt: str,
        system: str | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    async def _ask_anthropic(
        self,
        client: Any,
        prompt: str,
        system: str | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = await client.messages.create(**kwargs)
        return response.content[0].text

    async def _ask_gemini(
        self,
        model: Any,
        prompt: str,
        system: str | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        from google.generativeai.types import GenerationConfig

        # Если передан системный промпт, нужно пересоздать модель с ним
        if system:
            import google.generativeai as genai

            model = genai.GenerativeModel(
                model_name=self.config.model,
                system_instruction=system,
            )

        gen_config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        response = await model.generate_content_async(
            prompt,
            generation_config=gen_config,
        )
        return response.text

    # ── Жизненный цикл ──────────────────────────────────────────────────

    async def close(self) -> None:
        """Корректное завершение клиента (если поддерживается)."""
        if self._client and hasattr(self._client, "close"):
            await self._client.close()
        self._client = None
        logger.info("LLMEngine: клиент закрыт")
