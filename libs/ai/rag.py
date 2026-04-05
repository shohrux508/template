"""
libs.ai.rag — Векторный поиск и RAG-пайплайн (Qdrant).

Пример использования:
    rag = RAGService(RAGConfig(qdrant_url="http://localhost:6333"))
    await rag.index_documents("my_kb", documents)
    results = await rag.search("my_kb", "как перезагрузить датчик?")
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from loguru import logger


# ── Конфигурация ─────────────────────────────────────────────────────────────


class RAGConfig(BaseModel):
    """Настройки RAG-сервиса."""

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    collection_prefix: str = "rag"
    embedding_model: str = "text-embedding-3-small"
    embedding_api_key: str = ""
    embedding_dimensions: int = Field(default=1536, gt=0)
    top_k: int = Field(default=5, gt=0)


# ── Модели данных ────────────────────────────────────────────────────────────


class Document(BaseModel):
    """Документ для индексации."""

    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """Результат поиска."""

    id: str
    text: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Сервис ───────────────────────────────────────────────────────────────────


class RAGService:
    """Обертка для работы с векторным хранилищем Qdrant + embeddings."""

    def __init__(self, config: RAGConfig) -> None:
        self.config = config
        self._qdrant: Any = None
        self._embedder: Any = None
        logger.info("RAGService инициализирован (url={})", config.qdrant_url)

    # ── Ленивая инициализация ────────────────────────────────────────────

    async def _get_qdrant(self) -> Any:
        if self._qdrant is not None:
            return self._qdrant

        from qdrant_client import AsyncQdrantClient

        self._qdrant = AsyncQdrantClient(
            url=self.config.qdrant_url,
            api_key=self.config.qdrant_api_key,
        )
        return self._qdrant

    async def _get_embedder(self) -> Any:
        if self._embedder is not None:
            return self._embedder

        from openai import AsyncOpenAI

        self._embedder = AsyncOpenAI(api_key=self.config.embedding_api_key)
        return self._embedder

    # ── Embeddings ───────────────────────────────────────────────────────

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        """Получить эмбеддинги для списка текстов через OpenAI."""
        client = await self._get_embedder()
        response = await client.embeddings.create(
            model=self.config.embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    # ── Публичный API ────────────────────────────────────────────────────

    async def ensure_collection(self, name: str) -> None:
        """Создать коллекцию, если она не существует."""
        from qdrant_client.models import Distance, VectorParams

        qdrant = await self._get_qdrant()
        collection_name = f"{self.config.collection_prefix}_{name}"

        collections = await qdrant.get_collections()
        existing = [c.name for c in collections.collections]

        if collection_name not in existing:
            await qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.config.embedding_dimensions,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("RAG: Создана коллекция '{}'", collection_name)

    async def index_documents(self, name: str, documents: list[Document]) -> int:
        """Индексировать документы в коллекцию. Возвращает кол-во добавленных."""
        from qdrant_client.models import PointStruct

        await self.ensure_collection(name)
        qdrant = await self._get_qdrant()
        collection_name = f"{self.config.collection_prefix}_{name}"

        texts = [doc.text for doc in documents]
        embeddings = await self._embed(texts)

        points = [
            PointStruct(
                id=doc.id,
                vector=embedding,
                payload={"text": doc.text, **doc.metadata},
            )
            for doc, embedding in zip(documents, embeddings)
        ]

        await qdrant.upsert(collection_name=collection_name, points=points)
        logger.info("RAG: Индексировано {} документов в '{}'", len(points), collection_name)
        return len(points)

    async def search(
        self,
        name: str,
        query: str,
        *,
        top_k: int | None = None,
    ) -> list[SearchResult]:
        """Семантический поиск по коллекции."""
        qdrant = await self._get_qdrant()
        collection_name = f"{self.config.collection_prefix}_{name}"
        k = top_k or self.config.top_k

        query_embedding = (await self._embed([query]))[0]

        hits = await qdrant.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=k,
        )

        results = [
            SearchResult(
                id=str(hit.id),
                text=hit.payload.get("text", "") if hit.payload else "",
                score=hit.score,
                metadata={
                    k: v
                    for k, v in (hit.payload or {}).items()
                    if k != "text"
                },
            )
            for hit in hits
        ]

        logger.debug("RAG: Найдено {} результатов в '{}'", len(results), collection_name)
        return results

    # ── Жизненный цикл ──────────────────────────────────────────────────

    async def close(self) -> None:
        """Закрыть соединения."""
        if self._qdrant and hasattr(self._qdrant, "close"):
            await self._qdrant.close()
        if self._embedder and hasattr(self._embedder, "close"):
            await self._embedder.close()
        self._qdrant = None
        self._embedder = None
        logger.info("RAGService: соединения закрыты")
