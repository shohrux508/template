"""
libs.data.analysis — Обработка и анализ данных (Pandas / Numpy).

Все публичные методы возвращают Pydantic-модели, обеспечивая единую
типизацию от датчика до экрана телефона:
  - Бот берёт модель и отправляет пользователю.
  - API берёт ту же модель и отдаёт JSON.

Пример использования:
    svc = AnalysisService()
    result = svc.process_metrics([{"temp": 22.5, "hum": 60}, ...])
    result.summary   # MetricsSummary (Pydantic)
    result.df         # DataFrame (для viz)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from loguru import logger


# ── Модели данных (Pydantic — единый контракт для Bot / API) ─────────────────


class ColumnStats(BaseModel):
    """Статистика по одной числовой колонке."""

    mean: float = 0.0
    std: float = 0.0
    min: float = 0.0
    max: float = 0.0
    median: float = 0.0


class MetricsSummary(BaseModel):
    """Агрегированная статистика по набору данных."""

    count: int = 0
    columns: list[str] = Field(default_factory=list)
    stats: dict[str, ColumnStats] = Field(default_factory=dict)


class AnomalyReport(BaseModel):
    """Результат обнаружения аномалий."""

    total_values: int = 0
    anomaly_indices: list[int] = Field(default_factory=list)
    anomaly_count: int = 0
    threshold: float = 2.0


class OutlierReport(BaseModel):
    """Результат фильтрации выбросов."""

    original_count: int = 0
    filtered_count: int = 0
    removed_count: int = 0
    column: str = ""
    std_factor: float = 2.0


class AnalysisResult(BaseModel):
    """Универсальный результат анализа.

    Содержит Pydantic-сводку (для сериализации в JSON / отправки в Telegram)
    и ссылку на DataFrame (для визуализации / дальнейшей обработки).
    """

    summary: MetricsSummary = Field(default_factory=MetricsSummary)
    records: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}

    @property
    def df(self) -> Any:
        """Вернуть DataFrame из records (для передачи в VizService)."""
        import pandas as pd
        return pd.DataFrame(self.records) if self.records else pd.DataFrame()


class TimeSeriesConfig(BaseModel):
    """Настройки для анализа временных рядов."""

    time_column: str = "timestamp"
    value_column: str = "value"
    resample_rule: str | None = None  # Например "5min", "1h"
    fill_method: str = "ffill"


# ── Сервис ───────────────────────────────────────────────────────────────────


class AnalysisService:
    """Обертка для анализа данных через Pandas/Numpy.

    Все публичные методы возвращают Pydantic-модели для единого контракта.
    """

    def __init__(self) -> None:
        logger.info("AnalysisService инициализирован")

    # ── Основной метод ───────────────────────────────────────────────────

    def process_metrics(self, raw_data: list[dict[str, Any]]) -> AnalysisResult:
        """Превратить сырые данные в AnalysisResult (Pydantic).

        Возвращает объект, из которого можно:
          - result.summary     → MetricsSummary для JSON / Telegram
          - result.records     → list[dict] для сериализации
          - result.df          → DataFrame для VizService
        """
        import pandas as pd

        if not raw_data:
            logger.warning("process_metrics: пустой набор данных")
            return AnalysisResult()

        df = pd.DataFrame(raw_data)
        summary = self._build_summary(df)
        records = df.to_dict(orient="records")

        logger.info("process_metrics: {} строк, {} колонок", len(df), len(df.columns))
        return AnalysisResult(summary=summary, records=records)

    def describe(self, df: Any) -> MetricsSummary:
        """Получить статистическую сводку по DataFrame."""
        import pandas as pd

        if not isinstance(df, pd.DataFrame) or df.empty:
            return MetricsSummary()

        return self._build_summary(df)

    # ── Фильтрация и ресемплинг ──────────────────────────────────────────

    def filter_outliers(
        self,
        df: Any,
        column: str,
        *,
        std_factor: float = 2.0,
    ) -> OutlierReport:
        """Удалить выбросы. Возвращает Pydantic-отчёт.

        Отфильтрованный DataFrame доступен через повторный process_metrics.
        """
        import numpy as np

        original_count = len(df)
        mean = float(np.mean(df[column]))
        std = float(np.std(df[column]))

        filtered = df[
            (df[column] >= mean - std_factor * std)
            & (df[column] <= mean + std_factor * std)
        ]
        removed = original_count - len(filtered)

        if removed:
            logger.info("filter_outliers: удалено {} выбросов из '{}'", removed, column)

        return OutlierReport(
            original_count=original_count,
            filtered_count=len(filtered),
            removed_count=removed,
            column=column,
            std_factor=std_factor,
        )

    def filter_outliers_df(
        self,
        df: Any,
        column: str,
        *,
        std_factor: float = 2.0,
    ) -> Any:
        """Удалить выбросы и вернуть очищенный DataFrame (для цепочек)."""
        import numpy as np

        mean = float(np.mean(df[column]))
        std = float(np.std(df[column]))

        return df[
            (df[column] >= mean - std_factor * std)
            & (df[column] <= mean + std_factor * std)
        ]

    def resample_timeseries(self, df: Any, config: TimeSeriesConfig) -> AnalysisResult:
        """Ресемплинг временного ряда. Возвращает AnalysisResult."""
        import pandas as pd

        if config.time_column not in df.columns:
            raise ValueError(f"Колонка '{config.time_column}' не найдена в DataFrame")

        df = df.copy()
        df[config.time_column] = pd.to_datetime(df[config.time_column])
        df = df.set_index(config.time_column).sort_index()

        if config.resample_rule:
            df = df.resample(config.resample_rule).mean()
            if config.fill_method == "ffill":
                df = df.ffill()
            elif config.fill_method == "bfill":
                df = df.bfill()
            elif config.fill_method == "interpolate":
                df = df.interpolate()

        df = df.reset_index()
        logger.info("resample_timeseries: {} строк после ресемплинга", len(df))

        return AnalysisResult(
            summary=self._build_summary(df),
            records=df.to_dict(orient="records"),
        )

    # ── Numpy-утилиты (возвращают Pydantic где есть смысл) ───────────────

    @staticmethod
    def moving_average(values: list[float], window: int = 5) -> list[float]:
        """Скользящее среднее."""
        import numpy as np

        arr = np.array(values)
        if len(arr) < window:
            return values
        kernel = np.ones(window) / window
        return np.convolve(arr, kernel, mode="valid").tolist()

    @staticmethod
    def normalize(values: list[float]) -> list[float]:
        """Нормализация в диапазон [0, 1]."""
        import numpy as np

        arr = np.array(values, dtype=float)
        min_val, max_val = float(arr.min()), float(arr.max())
        if max_val == min_val:
            return [0.0] * len(values)
        return ((arr - min_val) / (max_val - min_val)).tolist()

    @staticmethod
    def detect_anomalies(
        values: list[float],
        *,
        threshold: float = 2.0,
    ) -> AnomalyReport:
        """Обнаружение аномалий по z-score. Возвращает Pydantic-отчёт."""
        import numpy as np

        arr = np.array(values)
        mean, std = float(arr.mean()), float(arr.std())

        if std == 0:
            return AnomalyReport(total_values=len(values), threshold=threshold)

        z_scores = np.abs((arr - mean) / std)
        indices = [int(i) for i in np.where(z_scores > threshold)[0]]

        return AnomalyReport(
            total_values=len(values),
            anomaly_indices=indices,
            anomaly_count=len(indices),
            threshold=threshold,
        )

    # ── Приватные хелперы ────────────────────────────────────────────────

    def _build_summary(self, df: Any) -> MetricsSummary:
        """Построить MetricsSummary из DataFrame."""
        numeric_cols = df.select_dtypes(include="number")
        desc = numeric_cols.describe()

        stats: dict[str, ColumnStats] = {}
        for col in desc.columns:
            stats[col] = ColumnStats(
                mean=float(desc[col].get("mean", 0)),
                std=float(desc[col].get("std", 0)),
                min=float(desc[col].get("min", 0)),
                max=float(desc[col].get("max", 0)),
                median=float(numeric_cols[col].median()),
            )

        return MetricsSummary(
            count=len(df),
            columns=list(df.columns),
            stats=stats,
        )
