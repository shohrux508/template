"""
libs.data.analysis — Обработка и анализ данных (Pandas / Numpy).

Пример использования:
    svc = AnalysisService()
    df = svc.process_metrics([{"temp": 22.5, "hum": 60}, ...])
    stats = svc.describe(df)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from loguru import logger


# ── Модели данных ────────────────────────────────────────────────────────────


class MetricsSummary(BaseModel):
    """Агрегированная статистика по набору данных."""

    count: int = 0
    columns: list[str] = Field(default_factory=list)
    stats: dict[str, dict[str, float]] = Field(default_factory=dict)


class TimeSeriesConfig(BaseModel):
    """Настройки для анализа временных рядов."""

    time_column: str = "timestamp"
    value_column: str = "value"
    resample_rule: str | None = None  # Например "5min", "1h"
    fill_method: str = "ffill"


# ── Сервис ───────────────────────────────────────────────────────────────────


class AnalysisService:
    """Обертка для анализа данных через Pandas/Numpy."""

    def __init__(self) -> None:
        logger.info("AnalysisService инициализирован")

    # ── DataFrame операции ───────────────────────────────────────────────

    def process_metrics(self, raw_data: list[dict[str, Any]]) -> Any:
        """Превратить сырые данные (список словарей) в DataFrame."""
        import pandas as pd

        if not raw_data:
            logger.warning("process_metrics: пустой набор данных")
            return pd.DataFrame()

        df = pd.DataFrame(raw_data)
        logger.info("process_metrics: {} строк, {} колонок", len(df), len(df.columns))
        return df

    def describe(self, df: Any) -> MetricsSummary:
        """Получить статистическую сводку по DataFrame."""
        import pandas as pd

        if not isinstance(df, pd.DataFrame) or df.empty:
            return MetricsSummary()

        numeric_cols = df.select_dtypes(include="number")
        desc = numeric_cols.describe()

        stats: dict[str, dict[str, float]] = {}
        for col in desc.columns:
            stats[col] = {
                "mean": float(desc[col].get("mean", 0)),
                "std": float(desc[col].get("std", 0)),
                "min": float(desc[col].get("min", 0)),
                "max": float(desc[col].get("max", 0)),
                "median": float(numeric_cols[col].median()),
            }

        return MetricsSummary(
            count=len(df),
            columns=list(df.columns),
            stats=stats,
        )

    def filter_outliers(
        self,
        df: Any,
        column: str,
        *,
        std_factor: float = 2.0,
    ) -> Any:
        """Удалить выбросы по правилу N стандартных отклонений."""
        import numpy as np

        mean = float(np.mean(df[column]))
        std = float(np.std(df[column]))

        filtered = df[
            (df[column] >= mean - std_factor * std)
            & (df[column] <= mean + std_factor * std)
        ]
        removed = len(df) - len(filtered)
        if removed:
            logger.info("filter_outliers: удалено {} выбросов из '{}'", removed, column)
        return filtered

    def resample_timeseries(self, df: Any, config: TimeSeriesConfig) -> Any:
        """Ресемплинг временного ряда."""
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

        logger.info("resample_timeseries: {} строк после ресемплинга", len(df))
        return df.reset_index()

    # ── Numpy-утилиты ────────────────────────────────────────────────────

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
    ) -> list[int]:
        """Обнаружение аномалий по z-score. Возвращает индексы аномальных значений."""
        import numpy as np

        arr = np.array(values)
        mean, std = float(arr.mean()), float(arr.std())
        if std == 0:
            return []
        z_scores = np.abs((arr - mean) / std)
        return [int(i) for i in np.where(z_scores > threshold)[0]]
