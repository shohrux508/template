"""
libs.data.viz — Визуализация данных (Matplotlib / Plotly).

Пример использования:
    viz = VizService()
    path = viz.render_plot(df, column="temperature", title="Температура за неделю")
    # path → "/tmp/plot_abc123.png" — готов к отправке в Telegram
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from loguru import logger


# ── Конфигурация ─────────────────────────────────────────────────────────────


class PlotConfig(BaseModel):
    """Настройки графика."""

    title: str = ""
    xlabel: str = ""
    ylabel: str = ""
    figsize: tuple[int, int] = (12, 6)
    style: str = "seaborn-v0_8-darkgrid"
    dpi: int = Field(default=150, gt=0)
    color: str = "#4C72B0"
    grid: bool = True
    output_dir: str = "./plots"


# ── Сервис ───────────────────────────────────────────────────────────────────


class VizService:
    """Обертка для генерации графиков через Matplotlib и Plotly."""

    def __init__(self, default_config: PlotConfig | None = None) -> None:
        self.default_config = default_config or PlotConfig()
        Path(self.default_config.output_dir).mkdir(parents=True, exist_ok=True)
        logger.info("VizService инициализирован (output={})", self.default_config.output_dir)

    # ── Matplotlib ───────────────────────────────────────────────────────

    def render_plot(
        self,
        df: Any,
        *,
        column: str | None = None,
        x_column: str | None = None,
        kind: str = "line",
        config: PlotConfig | None = None,
    ) -> str:
        """Сгенерировать .png график и вернуть путь к файлу.

        Args:
            df: pandas DataFrame с данными.
            column: Колонка для оси Y (если не указана — все числовые).
            x_column: Колонка для оси X (если не указана — индекс).
            kind: Тип графика: 'line', 'bar', 'scatter', 'hist', 'area'.
            config: Параметры графика (по умолчанию — self.default_config).
        """
        import matplotlib

        matplotlib.use("Agg")  # Без GUI
        import matplotlib.pyplot as plt

        cfg = config or self.default_config

        try:
            plt.style.use(cfg.style)
        except OSError:
            pass  # Стиль не найден — используем дефолтный

        fig, ax = plt.subplots(figsize=cfg.figsize, dpi=cfg.dpi)

        plot_kwargs: dict[str, Any] = {"kind": kind, "ax": ax, "color": cfg.color}
        if x_column:
            plot_kwargs["x"] = x_column

        if column:
            df[[column] + ([x_column] if x_column else [])].plot(**plot_kwargs)
        else:
            df.select_dtypes(include="number").plot(**plot_kwargs)

        if cfg.title:
            ax.set_title(cfg.title, fontsize=14, fontweight="bold")
        if cfg.xlabel:
            ax.set_xlabel(cfg.xlabel)
        if cfg.ylabel:
            ax.set_ylabel(cfg.ylabel)
        if cfg.grid:
            ax.grid(True, alpha=0.3)

        plt.tight_layout()

        filename = f"plot_{uuid.uuid4().hex[:8]}.png"
        filepath = str(Path(cfg.output_dir) / filename)
        fig.savefig(filepath)
        plt.close(fig)

        logger.info("VizService: график сохранен → {}", filepath)
        return filepath

    def render_multi_plot(
        self,
        df: Any,
        columns: list[str],
        *,
        config: PlotConfig | None = None,
    ) -> str:
        """Несколько линий на одном графике."""
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        cfg = config or self.default_config

        try:
            plt.style.use(cfg.style)
        except OSError:
            pass

        fig, ax = plt.subplots(figsize=cfg.figsize, dpi=cfg.dpi)

        for col in columns:
            if col in df.columns:
                ax.plot(df.index, df[col], label=col)

        ax.legend()
        if cfg.title:
            ax.set_title(cfg.title, fontsize=14, fontweight="bold")
        if cfg.grid:
            ax.grid(True, alpha=0.3)

        plt.tight_layout()

        filename = f"multi_{uuid.uuid4().hex[:8]}.png"
        filepath = str(Path(cfg.output_dir) / filename)
        fig.savefig(filepath)
        plt.close(fig)

        logger.info("VizService: мульти-график → {}", filepath)
        return filepath

    # ── Plotly (интерактивный) ────────────────────────────────────────────

    def render_interactive(
        self,
        df: Any,
        *,
        column: str,
        x_column: str | None = None,
        kind: str = "line",
        title: str = "",
    ) -> str:
        """Сгенерировать интерактивный HTML-график через Plotly."""
        import plotly.express as px

        plot_funcs = {
            "line": px.line,
            "bar": px.bar,
            "scatter": px.scatter,
            "area": px.area,
        }

        func = plot_funcs.get(kind, px.line)
        kwargs: dict[str, Any] = {"data_frame": df, "y": column, "title": title}
        if x_column:
            kwargs["x"] = x_column

        fig = func(**kwargs)

        filename = f"interactive_{uuid.uuid4().hex[:8]}.html"
        filepath = str(Path(self.default_config.output_dir) / filename)
        fig.write_html(filepath)

        logger.info("VizService: интерактивный график → {}", filepath)
        return filepath
